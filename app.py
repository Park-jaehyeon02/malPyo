"""
app.py - 말표(Mal-Pyo) 키오스크 UI

코레일 스타일 예매 카드 + 음성 입력 바.
스크롤 없이 한 화면에 모든 정보 표시.
예매 → 할인 → 결제 3단계 페이지 흐름.
"""

from __future__ import annotations

import time
import streamlit as st

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

# 페이지별 음성 인식 Mock 데이터
MOCK_VOICE_BOOKING = {
    "departure": "서울",
    "arrival": "전주",
    "time": "14:00",
    "passengers": 2,
    "speech": "서울에서 전주 가는 두시 버스 두 장이요",
}

MOCK_VOICE_DISCOUNT = {
    "discounts": ["child", "senior"],
    "speech": "한 명은 어린이, 한 명은 경로 할인이요",
}

MOCK_VOICE_PAYMENT = {
    "payment": "card",
    "speech": "카드로 결제할게요",
}

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
KIOSK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

/* ── 리셋 ── */
header[data-testid="stHeader"], footer, #MainMenu { display:none!important; }
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none!important; }

/* ── 배경 ── */
.stApp {
    background: linear-gradient(170deg, #0B1120 0%, #111827 50%, #0F172A 100%) !important;
}
section.main > div.block-container {
    padding: 0.5rem 2rem 1rem 2rem !important;
    max-width: 960px !important;
}

/* ── 타이포그래피 ── */
html, body, .stApp, .stApp p, .stApp span, .stApp div, .stApp label {
    color: #E2E8F0 !important;
    font-family: 'Noto Sans KR',sans-serif !important;
}

/* ── 상단 음성 바 (슬림) ── */
.voice-bar {
    background: rgba(30,41,59,0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 16px;
    padding: 0.6rem 1.2rem;
    display: flex; align-items: center; gap: 1rem;
    margin-bottom: 0.6rem;
}
.vb-icon {
    width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg,#3B82F6,#6366F1);
    display:flex; align-items:center; justify-content:center;
    font-size:20px; flex-shrink:0;
    animation: vb-glow 2.5s ease-in-out infinite;
}
@keyframes vb-glow {
    0%,100%{box-shadow:0 0 10px rgba(59,130,246,.2)}
    50%{box-shadow:0 0 25px rgba(99,102,241,.45)}
}
.vb-text { font-size:1.15rem; color:#F1F5F9!important; font-weight:700; }
.vb-sub { font-size:0.85rem; color:#94A3B8!important; }
.vb-wave { display:flex; align-items:center; gap:4px; height:30px; }
.vb-bar {
    width:4px; border-radius:2px;
    background:linear-gradient(180deg,#60A5FA,#3B82F6);
    animation: vb-bounce 1s ease-in-out infinite;
}
.vb-bar:nth-child(1){height:8px;animation-delay:0s}
.vb-bar:nth-child(2){height:14px;animation-delay:.08s}
.vb-bar:nth-child(3){height:22px;animation-delay:.16s}
.vb-bar:nth-child(4){height:28px;animation-delay:.24s}
.vb-bar:nth-child(5){height:22px;animation-delay:.32s}
.vb-bar:nth-child(6){height:14px;animation-delay:.40s}
.vb-bar:nth-child(7){height:8px;animation-delay:.48s}
@keyframes vb-bounce {
    0%,100%{transform:scaleY(.3);opacity:.4}
    50%{transform:scaleY(1);opacity:1}
}
.vb-bubble {
    background:rgba(59,130,246,.1); border:1px solid rgba(96,165,250,.25);
    border-radius:10px; padding:0.3rem 0.8rem; margin-top:0.2rem; display:inline-block;
}
.vb-bubble-text { font-size:1.05rem; color:#BFDBFE!important; font-weight:600; }
.processing-badge {
    font-size:1.1rem; color:#60A5FA!important; font-weight:700;
    animation: proc-blink 1.2s infinite;
}
@keyframes proc-blink { 0%,100%{opacity:1} 50%{opacity:.2} }

/* ── 메인 카드 (코레일 스타일 예매 영역) ── */
.booking-card {
    background: rgba(30,41,59,0.5);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(71,85,105,0.4);
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin: 0.3rem 0;
}
.card-title {
    font-size: 1.3rem; font-weight: 900; color: #F1F5F9 !important;
    margin-bottom: 1rem; display:flex; align-items:center; gap:0.5rem;
}
.card-title-badge {
    font-size:0.75rem; background:#3B82F6; color:#fff!important;
    padding:0.15rem 0.6rem; border-radius:20px; font-weight:700;
}

/* ── 스텝 인디케이터 ── */
.steps {
    display:flex; justify-content:center; gap:0.5rem;
    margin-bottom:0.8rem;
}
.step {
    display:flex; align-items:center; gap:0.3rem;
    font-size:0.85rem; font-weight:700; color:#475569!important;
}
.step.active { color:#3B82F6!important; }
.step.done { color:#34D399!important; }
.step-dot {
    width:28px; height:28px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:0.8rem; font-weight:900;
    background:rgba(71,85,105,0.4); color:#64748B!important;
    border:2px solid #334155;
}
.step.active .step-dot {
    background:linear-gradient(135deg,#3B82F6,#2563EB);
    color:#fff!important; border-color:#60A5FA;
    box-shadow:0 0 12px rgba(59,130,246,.3);
}
.step.done .step-dot {
    background:#059669; color:#fff!important; border-color:#34D399;
}
.step-line {
    width:40px; height:2px; background:#334155;
    margin:0 0.2rem; border-radius:1px;
}
.step-line.done { background:#059669; }
.step-line.active { background:#3B82F6; }

/* ── 폼 라벨 ── */
.field-label {
    font-size:0.9rem; font-weight:700; color:#94A3B8!important;
    margin-bottom:0.2rem; letter-spacing:0.03em;
}

/* ── Selectbox 오버라이드 ── */
.stSelectbox > div > div {
    background: rgba(15,23,42,0.8) !important;
    border: 2px solid rgba(71,85,105,0.5) !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    min-height: 50px !important;
}
.stSelectbox > div > div:hover {
    border-color: rgba(59,130,246,0.5) !important;
}
.stSelectbox label { display:none !important; }

/* ── Number Input 오버라이드 ── */
.stNumberInput > div > div > input {
    background: rgba(15,23,42,0.8) !important;
    border: 2px solid rgba(71,85,105,0.5) !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
    font-size: 1.3rem !important;
    font-weight: 900 !important;
    text-align: center !important;
}

/* ── 스왑 버튼 ── */
.swap-col .stButton > button {
    background: rgba(59,130,246,0.15) !important;
    border: 2px solid rgba(59,130,246,0.3) !important;
    border-radius: 50% !important;
    min-height: 50px !important;
    font-size: 1.3rem !important;
    padding: 0 !important;
    width: 50px !important;
    color: #60A5FA !important;
}

/* ── 일반 버튼 ── */
.stButton > button {
    background: rgba(30,41,59,0.7) !important;
    border: 2px solid rgba(71,85,105,0.5) !important;
    border-radius: 12px !important;
    color: #CBD5E1 !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    min-height: 50px !important;
    transition: all .15s ease;
}
.stButton > button:hover {
    background: rgba(59,130,246,0.12) !important;
    border-color: rgba(59,130,246,0.4) !important;
    color: #E2E8F0 !important;
    transform: translateY(-1px);
}

/* primary = 선택됨 */
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg,#2563EB,#3B82F6) !important;
    border:2px solid #60A5FA !important;
    color:#fff !important;
    box-shadow:0 0 15px rgba(59,130,246,.25);
}

/* ── CTA 버튼 ── */
.btn-cta .stButton > button {
    background: linear-gradient(135deg,#F59E0B,#D97706) !important;
    border:2px solid #FBBF24 !important;
    color:#000 !important;
    font-size:1.4rem !important; font-weight:900 !important;
    min-height:60px !important; border-radius:14px !important;
    box-shadow:0 4px 20px rgba(245,158,11,.25);
}
.btn-cta .stButton > button:hover {
    background:linear-gradient(135deg,#D97706,#B45309)!important;
    box-shadow:0 4px 30px rgba(245,158,11,.45);
    transform:translateY(-2px);
}
.btn-cta .stButton > button:disabled {
    background:rgba(30,41,59,.5)!important;
    border-color:rgba(71,85,105,.3)!important;
    color:#475569!important; box-shadow:none;
}

/* ── 뒤로 버튼 ── */
.btn-back .stButton > button {
    background:transparent!important;
    border:2px solid rgba(71,85,105,.4)!important;
    color:#94A3B8!important;
    min-height:44px!important; font-size:1rem!important;
}

/* ── 할인 카드 ── */
.discount-card {
    background:rgba(30,41,59,.5); border:2px solid rgba(71,85,105,.4);
    border-radius:16px; padding:1rem; text-align:center;
    transition:all .15s;
}
.discount-card:hover { border-color:rgba(59,130,246,.4); }
.discount-card.active {
    border-color:#3B82F6;
    background:rgba(59,130,246,.1);
    box-shadow:0 0 20px rgba(59,130,246,.15);
}
.dc-icon { font-size:2rem; margin-bottom:0.3rem; }
.dc-name { font-size:1.1rem; font-weight:800; color:#F1F5F9!important; }
.dc-rate { font-size:1.3rem; font-weight:900; color:#60A5FA!important; margin:0.2rem 0; }
.dc-desc { font-size:0.8rem; color:#64748B!important; }

/* ── 결제 요약 ── */
.price-table {
    background:rgba(15,23,42,.5);
    border:1px solid rgba(71,85,105,.3);
    border-radius:16px; padding:1.2rem 1.5rem;
    margin:0.8rem 0;
}
.price-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:0.5rem 0; font-size:1.1rem;
}
.price-row.total {
    border-top:2px solid rgba(71,85,105,.4);
    margin-top:0.5rem; padding-top:0.8rem;
    font-size:1.5rem; font-weight:900;
}
.price-label { color:#94A3B8!important; font-weight:600; }
.price-value { color:#F1F5F9!important; font-weight:800; }
.price-row.total .price-value { color:#F59E0B!important; }
.price-discount { color:#34D399!important; font-weight:700; }

/* ── 요약 바 ── */
.summary-bar {
    background:rgba(59,130,246,.06);
    border:1px solid rgba(59,130,246,.15);
    border-radius:12px; padding:0.6rem 1.2rem;
    margin-bottom:0.8rem; text-align:center;
    font-size:1.05rem; font-weight:700; color:#94A3B8!important;
}
.summary-bar strong { color:#F1F5F9!important; }

/* ── 완료 화면 ── */
.complete-box {
    text-align:center; padding:2rem;
    background:rgba(5,150,105,.06);
    border:1px solid rgba(16,185,129,.2);
    border-radius:20px; margin:1rem 0;
}
.complete-icon { font-size:4rem; margin-bottom:0.5rem; }
.complete-title { font-size:2rem; color:#34D399!important; font-weight:900; }
.complete-detail { font-size:1.1rem; color:#94A3B8!important; margin-top:0.5rem; line-height:1.7; }
.ticket-box {
    background:rgba(15,23,42,.6); border:1px dashed rgba(71,85,105,.5);
    border-radius:14px; padding:1.2rem; margin:1rem auto; max-width:400px;
}
.ticket-row {
    display:flex; justify-content:space-between; padding:0.3rem 0;
    font-size:1rem;
}
.ticket-label { color:#64748B!important; font-weight:600; }
.ticket-value { color:#F1F5F9!important; font-weight:800; }

/* ── 인원별 할인 행 ── */
.pax-row {
    background:rgba(15,23,42,.4);
    border:1px solid rgba(71,85,105,.25);
    border-radius:12px;
    padding:0.5rem 1rem;
    margin:0.3rem 0;
}
.pax-row-label {
    font-size:0.95rem; font-weight:800; color:#94A3B8!important;
    display:flex; align-items:center; gap:0.4rem;
    margin-bottom:0.15rem;
}
.pax-row-price {
    font-size:0.85rem; font-weight:700; color:#60A5FA!important;
    text-align:right; margin-top:0.2rem;
}

/* ── 푸터 ── */
.kiosk-footer {
    text-align:center; padding:0.5rem 0;
    font-size:0.8rem; color:#334155!important;
    margin-top:0.5rem;
}

/* ── 포커스 ── */
*:focus-visible { outline:3px solid #60A5FA!important; outline-offset:3px; }

/* ── 스크롤바 숨김 ── */
::-webkit-scrollbar { width:0; height:0; }
section.main { overflow:hidden !important; }
</style>
"""

st.markdown(KIOSK_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────────────────────────
VOICE_IDLE = "idle"
VOICE_LISTENING = "listening"
VOICE_PROCESSING = "processing"
VOICE_DONE = "done"

PAGE_BOOKING = "booking"
PAGE_DISCOUNT = "discount"
PAGE_PAYMENT = "payment"
PAGE_COMPLETE = "complete"

DEFAULTS: dict = {
    "voice_phase": VOICE_IDLE,
    "recognized_text": "",
    "page": PAGE_BOOKING,
    "sel_departure": "선택",
    "sel_arrival": "선택",
    "sel_time": "선택",
    "sel_passengers": 1,
    "sel_discounts": ["normal"],
    "sel_payment": None,
    "widget_key_version": 0,  # 음성 인식 후 위젯 갱신용
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
def handle_mic_click():
    st.session_state.voice_phase = VOICE_LISTENING
    st.session_state.recognized_text = ""


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


def handle_reset():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v if not isinstance(v, list) else v.copy()


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


def process_voice_result():
    """현재 페이지에 맞게 음성 인식 결과를 처리한다."""
    page = st.session_state.page

    # 위젯 키 버전 증가 → 위젯이 새로 생성되어 새 값 반영
    st.session_state.widget_key_version += 1

    if page == PAGE_BOOKING:
        m = MOCK_VOICE_BOOKING
        st.session_state.recognized_text = m["speech"]
        st.session_state.sel_departure = m["departure"]
        st.session_state.sel_arrival = m["arrival"]
        st.session_state.sel_time = m["time"]
        st.session_state.sel_passengers = m["passengers"]
        # 인원 수에 맞게 할인 리스트 초기화 (기본값: 일반)
        st.session_state.sel_discounts = ["normal"] * m["passengers"]

    elif page == PAGE_DISCOUNT:
        m = MOCK_VOICE_DISCOUNT
        st.session_state.recognized_text = m["speech"]
        pax = st.session_state.sel_passengers
        discounts = m["discounts"]
        # 인원 수에 맞게 할인 적용 (부족하면 normal로 채움)
        st.session_state.sel_discounts = (discounts + ["normal"] * pax)[:pax]

    elif page == PAGE_PAYMENT:
        m = MOCK_VOICE_PAYMENT
        st.session_state.recognized_text = m["speech"]
        st.session_state.sel_payment = m["payment"]


def render_voice_bar():
    phase = st.session_state.voice_phase
    page = st.session_state.page
    guide_title, guide_sub = get_voice_guide()

    # 버튼 라벨
    btn_label_map = {
        PAGE_BOOKING: "🎤 음성 예매",
        PAGE_DISCOUNT: "🎤 음성 할인",
        PAGE_PAYMENT: "🎤 음성 결제",
    }
    btn_label = btn_label_map.get(page, "🎤 음성 입력")

    if phase == VOICE_IDLE:
        col_bar, col_btn = st.columns([5, 2])
        with col_bar:
            st.markdown(
                f"""<div class="voice-bar"><div class="vb-icon">🎤</div>
                <div><div class="vb-text">{guide_title}</div>
                <div class="vb-sub">{guide_sub}</div></div></div>""",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='padding-top:0.3rem'></div>", unsafe_allow_html=True)
            st.button(btn_label, on_click=handle_mic_click, key="btn_mic", use_container_width=True)

    elif phase == VOICE_LISTENING:
        st.markdown(
            """<div class="voice-bar"><div class="vb-icon">🎤</div>
            <div class="vb-wave"><div class="vb-bar"></div><div class="vb-bar"></div>
            <div class="vb-bar"></div><div class="vb-bar"></div><div class="vb-bar"></div>
            <div class="vb-bar"></div><div class="vb-bar"></div></div>
            <div class="vb-text">듣고 있습니다...</div></div>""",
            unsafe_allow_html=True,
        )
        time.sleep(2)
        st.session_state.voice_phase = VOICE_PROCESSING
        st.rerun()

    elif phase == VOICE_PROCESSING:
        st.markdown(
            """<div class="voice-bar"><div class="vb-icon">🎤</div>
            <div class="processing-badge">🔄 알아듣는 중...</div></div>""",
            unsafe_allow_html=True,
        )
        time.sleep(1.5)
        process_voice_result()
        st.session_state.voice_phase = VOICE_DONE
        st.rerun()

    elif phase == VOICE_DONE:
        col_bar, col_btn = st.columns([5, 2])
        with col_bar:
            text = st.session_state.recognized_text
            st.markdown(
                f"""<div class="voice-bar"><div class="vb-icon">🎤</div>
                <div><div class="vb-sub">🗣️ 내가 한 말</div>
                <div class="vb-bubble"><span class="vb-bubble-text">"{text}"</span></div></div></div>""",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='padding-top:0.3rem'></div>", unsafe_allow_html=True)
            st.button("🎤 다시 말하기", on_click=handle_mic_click, key="btn_mic_r", use_container_width=True)


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
    page = st.session_state.page

    if page != PAGE_COMPLETE:
        render_voice_bar()
        render_steps()

    if page == PAGE_BOOKING:
        render_page_booking()
    elif page == PAGE_DISCOUNT:
        render_page_discount()
    elif page == PAGE_PAYMENT:
        render_page_payment()
    elif page == PAGE_COMPLETE:
        render_page_complete()

    st.markdown('<div class="kiosk-footer">말표 Mal-Pyo · 음성 키오스크</div>', unsafe_allow_html=True)


main()
