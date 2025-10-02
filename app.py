# app.py
# Streamlit PDF editor (Cloud friendly) — ใช้ PyMuPDF เรนเดอร์ภาพ (ไม่ต้องใช้ poppler)
# Run locally: streamlit run app.py

import io
from typing import Dict, List, Any

import streamlit as st
from streamlit_drawable_canvas import st_canvas
import fitz  # PyMuPDF
from PIL import Image

# ---------------------------
# App Config
# ---------------------------
st.set_page_config(
    page_title="PDF Editor — Minimal SPA",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

PRIMARY = "#0F172A"   # slate-900
SECONDARY = "#334155" # slate-700
ACCENT = "#2563EB"    # blue-600
BG_SOFT = "#F8FAFC"   # slate-50
BORDER = "#E2E8F0"    # slate-200

st.markdown(
    f"""
    <style>
    .block-container {{max-width: 1300px; padding-top: 1rem;}}
    header {{ visibility: hidden; }}
    .topbar {{
        display:flex; align-items:center; gap:.75rem; padding:.75rem 1rem;
        background:{BG_SOFT}; border:1px solid {BORDER}; border-radius:14px;
    }}
    .brand {{ font-weight:700; letter-spacing:.2px; color:{PRIMARY}; }}
    .pill {{
        padding:.15rem .6rem; border:1px solid {BORDER}; border-radius:999px;
        font-size:.8rem; color:{SECONDARY};
    }}
    .subtle {{ color:{SECONDARY}; font-size:.9rem; }}
    </style>
    """,
    unsafe_allow_html=True
)

with st.container():
    col_l, col_r = st.columns([1, 3])
    with col_l:
        st.markdown(
            f"""
            <div class="topbar">
                <span class="brand">PDF Editor</span>
                <span class="pill">ฟรี</span>
                <span class="pill">ออนไลน์</span>
                <span class="pill">โทนมินิมอล</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_r:
        st.write("")

st.write("")

# ---------------------------
# Sidebar
# ---------------------------
with st.sidebar:
    st.markdown("### ขั้นตอน")
    st.markdown("1) อัปโหลด PDF  \n2) แก้ไขบนแคนวาส  \n3) บันทึก/ดาวน์โหลด")
    st.divider()
    zoom = st.slider("ซูมหน้ากระดาษ", 50, 220, 120, help="ปรับขนาดแสดงผลหน้า PDF")
    stroke_width = st.slider("ความหนาเส้น", 1, 12, 3)
    stroke_color = st.color_picker("สีเส้น/ข้อความ", "#111827")
    fill_color = st.color_picker("สีพื้นวัตถุ (โปร่งใสไว้สวยกว่า)", "#00000000")
    font_size = st.slider("ขนาดตัวอักษร", 10, 72, 20)
    dpi = st.slider("คุณภาพเรนเดอร์ (DPI)", 96, 200, 150, help="ค่ามาก = ชัดขึ้น แต่ใช้หน่วยความจำมากขึ้น")
    st.caption("Tip: ใช้โหมด Text แล้วคลิกที่ภาพเพื่อวางข้อความ")

# ---------------------------
# Utils
# ---------------------------
@st.cache_data(show_spinner=False)
def render_pdf_to_images_pymupdf(pdf_bytes: bytes, dpi: int = 150) -> List[Image.Image]:
    """
    เรนเดอร์หน้า PDF เป็น PIL.Image ด้วย PyMuPDF (ไม่ต้องใช้ poppler)
    """
    images: List[Image.Image] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        # factor = dpi / 72  (72 dpi = 1.0)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            mode = "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            images.append(img)
    return images

def apply_annotations_to_pdf(src_pdf: bytes, annotations: Dict[int, List[Dict[str, Any]]], dpi_used: int) -> bytes:
    """
    วาดวัตถุจากแคนวาสกลับเข้า PDF ด้วย PyMuPDF
    แมปพิกัดจากขนาดภาพที่เรนเดอร์ด้วย dpi_used → ขนาดหน้าจริงของ PDF
    """
    doc = fitz.open(stream=src_pdf, filetype="pdf")
    out = io.BytesIO()

    # เตรียมสัดส่วนอ้างอิงตาม dpi_used
    ref_images = render_pdf_to_images_pymupdf(src_pdf, dpi=dpi_used)

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_w, page_h = page.rect.width, page.rect.height

        items = annotations.get(page_index, [])
        if not items:
            continue

        ref_img = ref_images[page_index]
        disp_w, disp_h = ref_img.size

        sx = page_w / disp_w
        sy = page_h / disp_h

        for item in items:
            t = item.get("type")
            props = item.get("props", {})
            stroke = props.get("stroke", "#000000")
            fill = props.get("fill", None)
            line_w = float(props.get("strokeWidth", 2))

            if t in ("rect", "ellipse"):
                left = float(props.get("left", 0)) * sx
                top = float(props.get("top", 0)) * sy
                width = float(props.get("width", 0)) * sx
                height = float(props.get("height", 0)) * sy
                rect = fitz.Rect(left, top, left + width, top + height)

                if t == "rect":
                    page.draw_rect(
                        rect,
                        color=hex_to_rgb(stroke),
                        fill=hex_to_rgb(fill) if fill and fill != "#00000000" else None,
                        width=line_w,
                    )
                else:
                    page.draw_oval(
                        rect,
                        color=hex_to_rgb(stroke),
                        fill=hex_to_rgb(fill) if fill and fill != "#00000000" else None,
                        width=line_w,
                    )

            elif t == "path":
                pts = []
                for p in props.get("path", []):
                    x = float(p[1]) * sx
                    y = float(p[2]) * sy
                    pts.append((x, y))
                if len(pts) >= 2:
                    page.draw_polyline(pts, color=hex_to_rgb(stroke), width=line_w)

            elif t == "line":
                x1 = float(props.get("x1", 0)) * sx
                y1 = float(props.get("y1", 0)) * sy
                x2 = float(props.get("x2", 0)) * sx
                y2 = float(props.get("y2", 0)) * sy
                page.draw_line(fitz.Point(x1, y1), fitz.Point(x2, y2), color=hex_to_rgb(stroke), width=line_w)

            elif t == "text":
                text_val = props.get("text", "")
                left = float(props.get("left", 0)) * sx
                top = float(props.get("top", 0)) * sy
                size = float(props.get("fontSize", 14))
                page.insert_text(fitz.Point(left, top + size), text_val, fontsize=size, color=hex_to_rgb(stroke))

    doc.save(out)
    doc.close()
    return out.getvalue()

def hex_to_rgb(h: str):
    if not h or h == "#00000000":
        return None
    h = h.lstrip("#")
    if len(h) == 8:  # RGBA → ตัด alpha
        h = h[:6]
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

# ---------------------------
# State
# ---------------------------
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "images" not in st.session_state:
    st.session_state.images = []
if "page_index" not in st.session_state:
    st.session_state.page_index = 0
if "annos" not in st.session_state:
    st.session_state.annos = {}  # page_index -> list objects

# ---------------------------
# Upload
# ---------------------------
uploaded = st.file_uploader("เลือกไฟล์ PDF เพื่อเริ่มแก้ไข", type=["pdf"], label_visibility="collapsed")

if uploaded is not None:
    st.session_state.pdf_bytes = uploaded.read()
    st.session_state.images = render_pdf_to_images_pymupdf(st.session_state.pdf_bytes, dpi=dpi)
    st.session_state.page_index = 0
    for i in range(len(st.session_state.images)):
        st.session_state.annos.setdefault(i, [])

if not st.session_state.pdf_bytes:
    st.info("อัปโหลดไฟล์ PDF เพื่อเริ่มใช้งาน")
    st.stop()

# ---------------------------
# Pager + Actions
# ---------------------------
pages = st.session_state.images
n_pages = len(pages)

c1, c2, c3, c4 = st.columns([2, 2, 2, 6], vertical_alignment="center")
with c1:
    st.markdown("**เลือกหน้า**")
    page_i = st.number_input(
        "page",
        min_value=1,
        max_value=n_pages,
        value=st.session_state.page_index + 1,
        label_visibility="collapsed",
    )
    if page_i - 1 != st.session_state.page_index:
        st.session_state.page_index = page_i - 1

with c2:
    if st.button("ล้างการแก้ไขหน้านี้", use_container_width=True):
        st.session_state.annos[st.session_state.page_index] = []

with c3:
    if st.button("บันทึกเป็น PDF", type="primary", use_container_width=True):
        with st.spinner("กำลังรวมการแก้ไขกลับเข้า PDF..."):
            pdf_out = apply_annotations_to_pdf(
                st.session_state.pdf_bytes,
                st.session_state.annos,
                dpi_used=dpi,
            )
        st.download_button(
            "ดาวน์โหลดไฟล์",
            data=pdf_out,
            file_name="edited.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

with c4:
    st.markdown('<div class="subtle">การเปลี่ยนแปลงจะยังไม่เขียนทับจนกว่าจะกด “บันทึกเป็น PDF”</div>', unsafe_allow_html=True)

st.divider()

# ---------------------------
# Canvas
# ---------------------------
img = pages[st.session_state.page_index]
disp_w = int(img.size[0] * (zoom / 100))
disp_h = int(img.size[1] * (zoom / 100))
img_disp = img.resize((disp_w, disp_h))

toolbar_col, canvas_col = st.columns([1.6, 5])

with toolbar_col:
    st.markdown("#### เครื่องมือ")
    mode = st.segmented_control(
        "โหมด",
        options=["🖊️ เส้น", "⬛ สี่เหลี่ยม", "⚪ วงรี", "↔️ เส้นตรง", "🔤 ข้อความ", "🧽 ลบ"],
        default="🖊️ เส้น",
        help="เลือกโหมดการวาด/เพิ่มข้อความ"
    )
    mapping = {
        "🖊️ เส้น": "freedraw",
        "⬛ สี่เหลี่ยม": "rect",
        "⚪ วงรี": "ellipse",
        "↔️ เส้นตรง": "line",
        "🔤 ข้อความ": "text",
        "🧽 ลบ": "transform",
    }
    drawing_mode = mapping[mode]
    st.caption("โหมดลบ: คลิกเลือกวัตถุ แล้วกดปุ่ม Backspace/Delete")

with canvas_col:
    json_data = st_canvas(
        fill_color=fill_color,
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_image=img_disp,
        update_streamlit=True,
        height=disp_h,
        width=disp_w,
        drawing_mode=drawing_mode,
        key=f"canvas_{st.session_state.page_index}",
        display_toolbar=True,
        initial_drawing={"version": "5.2.4", "objects": st.session_state.annos.get(st.session_state.page_index, [])},
        background_color="rgba(0,0,0,0)",
        font_size=font_size,
    )

# บันทึก annotation ของหน้านี้
if json_data and "objects" in json_data:
    st.session_state.annos[st.session_state.page_index] = json_data["objects"]

# ---------------------------
# Footer
# ---------------------------
st.write("")
st.markdown(
    "<div class='subtle'>เคล็ดลับ: หากต้องการแก้ไขข้อความยาว ๆ ให้ใช้ตัวแปลง PDF → Word แล้วอัปโหลดกลับมา</div>",
    unsafe_allow_html=True
)
