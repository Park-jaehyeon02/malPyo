"""
app.py - 말표(Mal-Pyo) 키오스크 UI

코레일 스타일 예매 카드 + 음성 입력 바.
스크롤 없이 한 화면에 모든 정보 표시.
예매 → 할인 → 결제 3단계 페이지 흐름.
"""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from engine import MalPyoEngine

logger = logging.getLogger("malpyo.app")

# ─────────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="말표 (Mal-Pyo) — 음성 키오스크",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# 데이터
# ─────────────────────────────────────────────────────────────
CITIES = ["선택", "서울", "대전", "대구", "부산", "광주", "전주", "강릉", "제주"]
TIME_SLOTS = ["선택", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]

DISCOUNTS = [
    {"id": "normal", "name": "일반", "rate": 0, "icon": "🧑", "desc": "할인 없음"},
    {"id": "disabled", "name": "장애인", "rate": 50, "icon": "♿", "desc": "장애인 복지 할인"},
    {"id": "senior", "name": "경로우대", "rate": 30, "icon": "👴", "desc": "만 65세 이상"},
    {"id": "child", "name": "어린이", "rate": 50, "icon": "👶", "desc": "만 6~12세"},
    {"id": "youth", "name": "청소년", "rate": 20, "icon": "🧑‍🎓", "desc": "만 13~18세"},
]

PAYMENTS = [
    {"id": "card", "name": "신용/체크카드", "icon": "💳"},
    {"id": "cash", "name": "현금", "icon": "💵"},
    {"id": "mobile", "name": "모바일페이", "icon": "📱"},
    {"id": "transfer", "name": "계좌이체", "icon": "🏦"},
]

PRICE_MAP = {
    ("서울", "전주"): 15000, ("서울", "대전"): 12000, ("서울", "대구"): 22000,
    ("서울", "부산"): 28000, ("서울", "광주"): 20000, ("서울", "강릉"): 18000,
    ("서울", "제주"): 45000,
}
DEFAULT_PRICE = 15000

# ─────────────────────────────────────────────────────────────
# 파이프라인 엔진 (세션 간 공유, 1회만 로드)
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine() -> MalPyoEngine:
    return MalPyoEngine()


# ─────────────────────────────────────────────────────────────
# CSS (외부 파일 로드)
# ─────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

def load_css():
    css_path = STATIC_DIR / "kiosk.css"
    css_text = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

load_css()


# ─────────────────────────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────────────────────────
VOICE_IDLE = "idle"
VOICE_PROCESSING = "processing"
VOICE_DONE = "done"

# 모드
MODE_SELECT = "select"       # 시작 화면 (모드 선택)
MODE_CLASSIC = "classic"     # 기존 모드 (수동 선택만)
MODE_VOICE = "voice"         # 대화형 모드 (음성 + 수동)

PAGE_BOOKING = "booking"
PAGE_DISCOUNT = "discount"
PAGE_PAYMENT = "payment"
PAGE_COMPLETE = "complete"

DEFAULTS: dict = {
    "mode": MODE_SELECT,      # 현재 모드
    "voice_phase": VOICE_IDLE,
    "recognized_text": "",
    "reply_text": "",          # LLM 응답 텍스트
    "reply_audio": None,       # TTS 음성 bytes
    "page": PAGE_BOOKING,
    "sel_departure": "선택",
    "sel_arrival": "선택",
    "sel_time": "선택",
    "sel_passengers": 1,
    "sel_discounts": ["normal"],
    "sel_payment": None,
    "widget_key_version": 0,
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v if not isinstance(_v, list) else _v.copy()


# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def get_price() -> int:
    dep = st.session_state.sel_departure
    arr = st.session_state.sel_arrival
    return PRICE_MAP.get((dep, arr), PRICE_MAP.get((arr, dep), DEFAULT_PRICE))


def get_discount_by_id(discount_id: str) -> dict:
    for d in DISCOUNTS:
        if d["id"] == discount_id:
            return d
    return DISCOUNTS[0]


def sync_discounts_length():
    """인원 수에 맞게 할인 리스트 길이를 동기화한다."""
    pax = st.session_state.sel_passengers
    current = st.session_state.sel_discounts
    if len(current) < pax:
        current.extend(["normal"] * (pax - len(current)))
    elif len(current) > pax:
        st.session_state.sel_discounts = current[:pax]


def calc_total() -> tuple[int, int, int]:
    """(기본운임 합계, 할인 합계, 최종 금액) 반환."""
    base_unit = get_price()
    pax = st.session_state.sel_passengers
    sync_discounts_length()
    total_base = base_unit * pax
    total_discount = 0
    for disc_id in st.session_state.sel_discounts:
        info = get_discount_by_id(disc_id)
        total_discount += int(base_unit * info["rate"] / 100)
    return total_base, total_discount, total_base - total_discount


def can_proceed_booking() -> bool:
    return all([
        st.session_state.sel_departure != "선택",
        st.session_state.sel_arrival != "선택",
        st.session_state.sel_time != "선택",
        st.session_state.sel_departure != st.session_state.sel_arrival,
    ])


# ─────────────────────────────────────────────────────────────
# 핸들러
# ─────────────────────────────────────────────────────────────
def handle_voice_reset():
    """음성 바를 초기 상태로 되돌린다."""
    st.session_state.voice_phase = VOICE_IDLE
    st.session_state.recognized_text = ""
    st.session_state.widget_key_version += 1


def handle_swap():
    dep = st.session_state.sel_departure
    arr = st.session_state.sel_arrival
    st.session_state.sel_departure = arr
    st.session_state.sel_arrival = dep


def handle_go(page: str):
    st.session_state.page = page
    # 페이지 이동 시 음성 상태 초기화
    st.session_state.voice_phase = VOICE_IDLE
    st.session_state.recognized_text = ""


def handle_select_payment(payment_id: str):
    st.session_state.sel_payment = payment_id


def handle_select_mode(mode: str):
    st.session_state.mode = mode
    st.session_state.page = PAGE_BOOKING


def handle_reset():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v if not isinstance(v, list) else v.copy()


# ─────────────────────────────────────────────────────────────
# 시작 화면 (모드 선택)
# ─────────────────────────────────────────────────────────────
def render_mode_select():
    st.markdown(
        """<div style="text-align:center;padding:2rem 0 1rem">
        <div style="font-size:3.5rem;margin-bottom:0.5rem">🐴</div>
        <div style="font-size:2.2rem;font-weight:900;color:#F8FAFC;margin-bottom:0.3rem">말표 Mal-Pyo</div>
        <div style="font-size:1.1rem;color:#94A3B8">음성 기반 교통 예매 키오스크</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div style="text-align:center;margin:1.5rem 0 2rem;color:#CBD5E1;font-size:1rem">
        이용 방식을 선택해 주세요
        </div>""",
        unsafe_allow_html=True,
    )

    _, col_classic, col_voice, _ = st.columns([1, 2, 2, 1])

    with col_classic:
        st.markdown(
            """<div class="booking-card" style="text-align:center;padding:2rem 1rem;min-height:220px">
            <div style="font-size:3rem;margin-bottom:0.8rem">🖱️</div>
            <div style="font-size:1.3rem;font-weight:700;color:#F8FAFC;margin-bottom:0.5rem">기존 모드</div>
            <div style="font-size:0.9rem;color:#94A3B8;line-height:1.5">
            화면을 터치하여<br>직접 선택합니다
            </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "🖱️  기존 모드로 시작",
            key="btn_mode_classic",
            on_click=handle_select_mode,
            args=(MODE_CLASSIC,),
            use_container_width=True,
        )

    with col_voice:
        st.markdown(
            """<div class="booking-card" style="text-align:center;padding:2rem 1rem;min-height:220px">
            <div style="font-size:3rem;margin-bottom:0.8rem">🎤</div>
            <div style="font-size:1.3rem;font-weight:700;color:#F8FAFC;margin-bottom:0.5rem">대화형 모드</div>
            <div style="font-size:0.9rem;color:#94A3B8;line-height:1.5">
            음성으로 말하면<br>자동으로 입력됩니다
            </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "🎤  대화형 모드로 시작",
            key="btn_mode_voice",
            on_click=handle_select_mode,
            args=(MODE_VOICE,),
            use_container_width=True,
            type="primary",
        )

    st.markdown(
        """<div style="text-align:center;margin-top:2rem;padding:1rem;
        background:rgba(59,130,246,0.1);border-radius:12px;border:1px solid rgba(59,130,246,0.3)">
        <div style="font-size:0.95rem;color:#60A5FA">💡 대화형 모드에서도 화면 터치로 직접 선택할 수 있습니다</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# 스텝 인디케이터
# ─────────────────────────────────────────────────────────────
def render_steps():
    page = st.session_state.page
    pages = [PAGE_BOOKING, PAGE_DISCOUNT, PAGE_PAYMENT]
    labels = ["예매", "할인", "결제"]
    current_idx = pages.index(page) if page in pages else 3

    parts = []
    for i, label in enumerate(labels):
        if i < current_idx:
            cls = "done"
            dot = "✓"
        elif i == current_idx:
            cls = "active"
            dot = str(i + 1)
        else:
            cls = ""
            dot = str(i + 1)
        parts.append(f'<div class="step {cls}"><div class="step-dot">{dot}</div>{label}</div>')
        if i < len(labels) - 1:
            line_cls = "done" if i < current_idx else ("active" if i == current_idx else "")
            parts.append(f'<div class="step-line {line_cls}"></div>')

    st.markdown(f'<div class="steps">{"".join(parts)}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 상단 음성 바 — 페이지별로 다른 안내 및 처리
# ─────────────────────────────────────────────────────────────
def get_voice_guide() -> tuple[str, str]:
    """현재 페이지에 맞는 음성 안내 문구를 반환한다."""
    page = st.session_state.page
    if page == PAGE_BOOKING:
        return "말씀만 하세요", "출발지, 도착지, 시간, 인원을 말해주세요"
    elif page == PAGE_DISCOUNT:
        return "할인을 말씀하세요", "각 탑승객의 할인 유형을 말해주세요"
    elif page == PAGE_PAYMENT:
        return "결제수단을 말씀하세요", "카드, 현금, 모바일페이, 계좌이체 중 선택"
    return "말씀만 하세요", "음성으로 입력할 수 있어요"


def process_voice_result(audio_bytes: bytes):
    """녹음된 오디오를 파이프라인(STT→LLM→TTS)으로 처리한다."""
    page = st.session_state.page
    context = {"passengers": st.session_state.sel_passengers}

    engine = get_engine()
    result = engine.process(audio_bytes, page, context)

    st.session_state.recognized_text = result.recognized_text
    st.session_state.reply_text = result.reply_text
    st.session_state.reply_audio = result.reply_audio
    st.session_state.widget_key_version += 1

    if not result.success:
        return

    parsed = result.parsed

    # 페이지별로 파싱된 데이터를 폼에 반영
    if page == PAGE_BOOKING:
        if parsed.get("departure") and parsed["departure"] in CITIES:
            st.session_state.sel_departure = parsed["departure"]
        if parsed.get("arrival") and parsed["arrival"] in CITIES:
            st.session_state.sel_arrival = parsed["arrival"]
        if parsed.get("time") and parsed["time"] in TIME_SLOTS:
            st.session_state.sel_time = parsed["time"]
        if parsed.get("passengers"):
            pax = int(parsed["passengers"])
            st.session_state.sel_passengers = max(1, min(9, pax))
            st.session_state.sel_discounts = ["normal"] * st.session_state.sel_passengers

    elif page == PAGE_DISCOUNT:
        if parsed.get("discounts"):
            pax = st.session_state.sel_passengers
            valid_ids = [d["id"] for d in DISCOUNTS]
            discounts = [d if d in valid_ids else "normal" for d in parsed["discounts"]]
            st.session_state.sel_discounts = (discounts + ["normal"] * pax)[:pax]

    elif page == PAGE_PAYMENT:
        if parsed.get("payment"):
            valid_ids = [p["id"] for p in PAYMENTS]
            if parsed["payment"] in valid_ids:
                st.session_state.sel_payment = parsed["payment"]


def render_voice_bar():
    phase = st.session_state.voice_phase
    v = st.session_state.widget_key_version
    guide_title, guide_sub = get_voice_guide()

    if phase == VOICE_IDLE:
        col_guide, col_rec = st.columns([3, 4])
        with col_guide:
            st.markdown(
                f"""<div class="voice-bar"><div class="vb-icon">🎤</div>
                <div><div class="vb-text">{guide_title}</div>
                <div class="vb-sub">{guide_sub}</div></div></div>""",
                unsafe_allow_html=True,
            )
        with col_rec:
            audio_data = st.audio_input(
                "음성을 녹음하세요",
                key=f"audio_rec_{v}",
                label_visibility="collapsed",
            )
            if audio_data is not None:
                st.session_state._pending_audio = audio_data.getvalue()
                st.session_state.voice_phase = VOICE_PROCESSING
                st.rerun()

    elif phase == VOICE_PROCESSING:
        st.markdown(
            """<div class="voice-bar"><div class="vb-icon">🎤</div>
            <div class="vb-wave"><div class="vb-bar"></div><div class="vb-bar"></div>
            <div class="vb-bar"></div><div class="vb-bar"></div><div class="vb-bar"></div>
            <div class="vb-bar"></div><div class="vb-bar"></div></div>
            <div class="processing-badge">🔄 알아듣는 중...</div></div>""",
            unsafe_allow_html=True,
        )
        audio_bytes = st.session_state.get("_pending_audio")
        if audio_bytes:
            process_voice_result(audio_bytes)
            st.session_state._pending_audio = None
        st.session_state.voice_phase = VOICE_DONE
        st.rerun()

    elif phase == VOICE_DONE:
        recognized = st.session_state.recognized_text
        reply = st.session_state.get("reply_text", "")
        reply_audio = st.session_state.get("reply_audio")

        col_bar, col_btn = st.columns([5, 2])
        with col_bar:
            # 내가 한 말
            st.markdown(
                f"""<div class="voice-bar"><div class="vb-icon">🎤</div>
                <div><div class="vb-sub">🗣️ 내가 한 말</div>
                <div class="vb-bubble"><span class="vb-bubble-text">"{recognized}"</span></div></div></div>""",
                unsafe_allow_html=True,
            )
            # AI 응답 텍스트
            if reply:
                st.markdown(
                    f"""<div class="voice-bar" style="border-color:rgba(52,211,153,.3)">
                    <div class="vb-icon" style="background:linear-gradient(135deg,#059669,#34D399)">🤖</div>
                    <div><div class="vb-sub" style="color:#34D399!important">🤖 말표 응답</div>
                    <div class="vb-bubble" style="background:rgba(5,150,105,.1);border-color:rgba(52,211,153,.25)">
                    <span class="vb-bubble-text" style="color:#A7F3D0!important">{reply}</span></div></div></div>""",
                    unsafe_allow_html=True,
                )
        with col_btn:
            st.markdown("<div style='padding-top:0.3rem'></div>", unsafe_allow_html=True)
            st.button("🎤 다시 말하기", on_click=handle_voice_reset, key="btn_mic_r", use_container_width=True)

        # TTS 음성 자동 재생
        if reply_audio:
            st.audio(reply_audio, format="audio/wav", autoplay=True)


# ─────────────────────────────────────────────────────────────
# PAGE 1: 예매
# ─────────────────────────────────────────────────────────────
def render_page_booking():
    st.markdown(
        '<div class="booking-card">'
        '<div class="card-title">🚌 승차권 예매 <span class="card-title-badge">STEP 1</span></div>',
        unsafe_allow_html=True,
    )

    # 위젯 키 버전 (음성 인식 후 위젯 갱신용)
    v = st.session_state.widget_key_version

    # 출발 / 스왑 / 도착
    col_dep, col_swap, col_arr = st.columns([5, 1, 5])
    with col_dep:
        st.markdown('<div class="field-label">출발지</div>', unsafe_allow_html=True)
        dep_idx = CITIES.index(st.session_state.sel_departure) if st.session_state.sel_departure in CITIES else 0
        dep = st.selectbox("출발", CITIES, index=dep_idx, key=f"sb_dep_{v}", label_visibility="collapsed")
        if dep != st.session_state.sel_departure:
            st.session_state.sel_departure = dep
    with col_swap:
        st.markdown('<div class="field-label" style="text-align:center">&nbsp;</div>', unsafe_allow_html=True)
        st.markdown('<div class="swap-col">', unsafe_allow_html=True)
        st.button("⇄", key=f"btn_swap_{v}", on_click=handle_swap, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_arr:
        st.markdown('<div class="field-label">도착지</div>', unsafe_allow_html=True)
        arr_idx = CITIES.index(st.session_state.sel_arrival) if st.session_state.sel_arrival in CITIES else 0
        arr = st.selectbox("도착", CITIES, index=arr_idx, key=f"sb_arr_{v}", label_visibility="collapsed")
        if arr != st.session_state.sel_arrival:
            st.session_state.sel_arrival = arr

    # 시간 / 인원
    col_time, col_pax = st.columns([6, 5])
    with col_time:
        st.markdown('<div class="field-label">출발 시간</div>', unsafe_allow_html=True)
        tm_idx = TIME_SLOTS.index(st.session_state.sel_time) if st.session_state.sel_time in TIME_SLOTS else 0
        tm = st.selectbox("시간", TIME_SLOTS, index=tm_idx, key=f"sb_time_{v}", label_visibility="collapsed")
        if tm != st.session_state.sel_time:
            st.session_state.sel_time = tm
    with col_pax:
        st.markdown('<div class="field-label">인원</div>', unsafe_allow_html=True)
        pax = st.number_input("인원", min_value=1, max_value=9, value=st.session_state.sel_passengers, key=f"ni_pax_{v}", label_visibility="collapsed")
        if pax != st.session_state.sel_passengers:
            st.session_state.sel_passengers = pax

    st.markdown("</div>", unsafe_allow_html=True)

    # 출발/도착 같은 경우 경고
    if (st.session_state.sel_departure != "선택"
        and st.session_state.sel_arrival != "선택"
        and st.session_state.sel_departure == st.session_state.sel_arrival):
        st.warning("출발지와 도착지가 같습니다. 다시 선택해 주세요.")

    # CTA
    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
    ok = can_proceed_booking()
    st.markdown('<div class="btn-cta">', unsafe_allow_html=True)
    st.button(
        "다음 단계 → 할인 선택" if ok else "출발지 · 도착지 · 시간을 선택해 주세요",
        on_click=handle_go if ok else None,
        args=(PAGE_DISCOUNT,) if ok else None,
        key="btn_next1",
        use_container_width=True,
        disabled=not ok,
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PAGE 2: 할인 (인원별 개별 선택)
# ─────────────────────────────────────────────────────────────
DISCOUNT_OPTIONS = [f"{d['icon']} {d['name']} ({d['rate']}%)" if d["rate"] > 0 else f"{d['icon']} {d['name']} (정상가)" for d in DISCOUNTS]
DISCOUNT_IDS = [d["id"] for d in DISCOUNTS]


def render_page_discount():
    dep = st.session_state.sel_departure
    arr = st.session_state.sel_arrival
    tm = st.session_state.sel_time
    pax = st.session_state.sel_passengers
    base_unit = get_price()
    v = st.session_state.widget_key_version  # 위젯 키 버전

    sync_discounts_length()

    st.markdown(
        f'<div class="summary-bar"><strong>{dep}</strong> → <strong>{arr}</strong>'
        f' · {tm} · {pax}명 · 1인 기본 운임 <strong>{base_unit:,}원</strong></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="booking-card">'
        '<div class="card-title">🏷️ 인원별 할인 선택 <span class="card-title-badge">STEP 2</span></div>',
        unsafe_allow_html=True,
    )

    for i in range(pax):
        current_id = st.session_state.sel_discounts[i]
        current_idx = DISCOUNT_IDS.index(current_id) if current_id in DISCOUNT_IDS else 0
        current_info = get_discount_by_id(current_id)
        per_price = base_unit - int(base_unit * current_info["rate"] / 100)

        st.markdown(f'<div class="pax-row">', unsafe_allow_html=True)
        col_label, col_select, col_price = st.columns([2, 5, 2])
        with col_label:
            st.markdown(
                f'<div class="pax-row-label">👤 탑승객 {i + 1}</div>',
                unsafe_allow_html=True,
            )
        with col_select:
            selected = st.selectbox(
                f"탑승객 {i+1} 할인",
                DISCOUNT_OPTIONS,
                index=current_idx,
                key=f"dc_sel_{v}_{i}",
                label_visibility="collapsed",
            )
            new_idx = DISCOUNT_OPTIONS.index(selected)
            st.session_state.sel_discounts[i] = DISCOUNT_IDS[new_idx]
        with col_price:
            st.markdown(
                f'<div class="pax-row-price">{per_price:,}원</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 가격 합산
    total_base, total_disc, final = calc_total()

    # 가격표 시작
    st.markdown(
        f'<div class="price-table">'
        f'<div class="price-row"><span class="price-label">기본 운임 ({pax}명)</span>'
        f'<span class="price-value">{total_base:,}원</span></div>',
        unsafe_allow_html=True,
    )

    # 할인 행들
    for i in range(pax):
        info = get_discount_by_id(st.session_state.sel_discounts[i])
        amt = int(base_unit * info["rate"] / 100)
        if amt > 0:
            st.markdown(
                f'<div class="price-row"><span class="price-label">탑승객 {i+1} · {info["name"]}</span>'
                f'<span class="price-discount">-{amt:,}원</span></div>',
                unsafe_allow_html=True,
            )

    # 가격표 종료
    st.markdown(
        f'<div class="price-row total"><span class="price-label">결제 금액</span>'
        f'<span class="price-value">{final:,}원</span></div></div>',
        unsafe_allow_html=True,
    )

    col_back, col_next = st.columns([1, 3])
    with col_back:
        st.markdown('<div class="btn-back">', unsafe_allow_html=True)
        st.button("← 이전", on_click=handle_go, args=(PAGE_BOOKING,), key="btn_back2", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_next:
        st.markdown('<div class="btn-cta">', unsafe_allow_html=True)
        st.button(
            f"결제하기 → {final:,}원",
            on_click=handle_go, args=(PAGE_PAYMENT,),
            key="btn_next2", use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PAGE 3: 결제
# ─────────────────────────────────────────────────────────────
def render_page_payment():
    dep = st.session_state.sel_departure
    arr = st.session_state.sel_arrival
    tm = st.session_state.sel_time
    pax = st.session_state.sel_passengers
    base_unit = get_price()
    total_base, total_disc, final = calc_total()

    disc_summary = ", ".join(
        get_discount_by_id(d)["name"] for d in st.session_state.sel_discounts
    )

    st.markdown(
        f'<div class="summary-bar"><strong>{dep}</strong> → <strong>{arr}</strong>'
        f' · {tm} · {pax}명 · {disc_summary}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="booking-card">'
        '<div class="card-title">💳 결제 수단 <span class="card-title-badge">STEP 3</span></div>',
        unsafe_allow_html=True,
    )

    v = st.session_state.widget_key_version  # 위젯 키 버전
    cols = st.columns(len(PAYMENTS), gap="small")
    for i, p in enumerate(PAYMENTS):
        with cols[i]:
            is_active = st.session_state.sel_payment == p["id"]
            st.button(
                f"{p['icon']}\n{p['name']}",
                key=f"pay_{v}_{p['id']}",
                on_click=handle_select_payment,
                args=(p["id"],),
                use_container_width=True,
                type="primary" if is_active else "secondary",
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # 인원별 가격 명세 - 가격표 시작
    st.markdown('<div class="price-table">', unsafe_allow_html=True)

    for i in range(pax):
        info = get_discount_by_id(st.session_state.sel_discounts[i])
        disc_amt = int(base_unit * info["rate"] / 100)
        per_price = base_unit - disc_amt
        tag = f' <span class="price-discount">(-{info["rate"]}%)</span>' if info["rate"] > 0 else ""
        st.markdown(
            f'<div class="price-row"><span class="price-label">탑승객 {i+1} · {info["name"]}{tag}</span>'
            f'<span class="price-value">{per_price:,}원</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="price-row total"><span class="price-label">총 결제 금액</span>'
        f'<span class="price-value">{final:,}원</span></div></div>',
        unsafe_allow_html=True,
    )

    has_payment = st.session_state.sel_payment is not None
    col_back, col_next = st.columns([1, 3])
    with col_back:
        st.markdown('<div class="btn-back">', unsafe_allow_html=True)
        st.button("← 이전", on_click=handle_go, args=(PAGE_DISCOUNT,), key="btn_back3", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_next:
        st.markdown('<div class="btn-cta">', unsafe_allow_html=True)
        st.button(
            f"💳 {final:,}원 결제하기" if has_payment else "결제 수단을 선택해 주세요",
            on_click=handle_go if has_payment else None,
            args=(PAGE_COMPLETE,) if has_payment else None,
            key="btn_pay", use_container_width=True,
            disabled=not has_payment,
        )
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PAGE 4: 완료
# ─────────────────────────────────────────────────────────────
def render_page_complete():
    dep = st.session_state.sel_departure
    arr = st.session_state.sel_arrival
    tm = st.session_state.sel_time
    pax = st.session_state.sel_passengers
    payment = next((p for p in PAYMENTS if p["id"] == st.session_state.sel_payment), PAYMENTS[0])
    base_unit = get_price()
    _, _, final = calc_total()

    # 인원별 할인 내역
    pax_lines = ""
    for i in range(pax):
        info = get_discount_by_id(st.session_state.sel_discounts[i])
        per = base_unit - int(base_unit * info["rate"] / 100)
        pax_lines += (
            f'<div class="ticket-row"><span class="ticket-label">탑승객 {i+1} ({info["name"]})</span>'
            f'<span class="ticket-value">{per:,}원</span></div>'
        )

    st.markdown(
        f"""<div class="complete-box">
        <div class="complete-icon">🎉</div>
        <div class="complete-title">예매가 완료되었습니다</div>
        <div class="complete-detail">승차권이 발권되었습니다</div>
        <div class="ticket-box">
            <div class="ticket-row"><span class="ticket-label">구간</span><span class="ticket-value">{dep} → {arr}</span></div>
            <div class="ticket-row"><span class="ticket-label">시간</span><span class="ticket-value">{tm}</span></div>
            <div class="ticket-row"><span class="ticket-label">인원</span><span class="ticket-value">{pax}명</span></div>
            <div class="ticket-row" style="border-top:1px dashed rgba(71,85,105,.3);margin-top:0.3rem;padding-top:0.3rem;"></div>
            {pax_lines}
            <div class="ticket-row"><span class="ticket-label">결제 수단</span><span class="ticket-value">{payment['icon']} {payment['name']}</span></div>
            <div class="ticket-row" style="border-top:1px dashed rgba(71,85,105,.5);margin-top:0.5rem;padding-top:0.5rem;">
                <span class="ticket-label" style="font-weight:900">결제 금액</span>
                <span class="ticket-value" style="color:#F59E0B!important;font-size:1.3rem">{final:,}원</span>
            </div>
        </div></div>""",
        unsafe_allow_html=True,
    )

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="btn-cta">', unsafe_allow_html=True)
        st.button("🏠  처음으로", on_click=handle_reset, use_container_width=True, key="btn_home")
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────
def main():
    mode = st.session_state.mode
    page = st.session_state.page

    # 모드 선택 화면
    if mode == MODE_SELECT:
        render_mode_select()
        st.markdown('<div class="kiosk-footer">말표 Mal-Pyo · 음성 키오스크</div>', unsafe_allow_html=True)
        return

    # 대화형 모드: 음성 바 표시 (완료 페이지 제외)
    if mode == MODE_VOICE and page != PAGE_COMPLETE:
        render_voice_bar()

    # 스텝 인디케이터 (완료 페이지 제외)
    if page != PAGE_COMPLETE:
        render_steps()

    # 페이지별 렌더링
    if page == PAGE_BOOKING:
        render_page_booking()
    elif page == PAGE_DISCOUNT:
        render_page_discount()
    elif page == PAGE_PAYMENT:
        render_page_payment()
    elif page == PAGE_COMPLETE:
        render_page_complete()

    # 푸터
    mode_label = "대화형 모드" if mode == MODE_VOICE else "기존 모드"
    st.markdown(f'<div class="kiosk-footer">말표 Mal-Pyo · {mode_label}</div>', unsafe_allow_html=True)


main()
