import io, os, glob
from typing import Dict, List, Any, Optional

import streamlit as st
from streamlit_drawable_canvas import st_canvas
import fitz  # PyMuPDF
from PIL import Image

# ---------------- Config ----------------
st.set_page_config(page_title="PDF Editor", page_icon="📝", layout="wide")

# ---------------- Utils ----------------
@st.cache_data(show_spinner=False)
def list_fonts(font_dir="fonts") -> List[str]:
    if not os.path.isdir(font_dir):
        return []
    files = sorted(glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf")))
    return [os.path.basename(f) for f in files]

@st.cache_data(show_spinner=False)
def render_page_image(pdf_bytes: bytes, page_index: int, dpi: int) -> Image.Image:
    """เรนเดอร์หน้าเดียวเป็นภาพ (Lazy-render)"""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        page = doc[page_index]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

@st.cache_data(show_spinner=False)
def get_page_count(pdf_bytes: bytes) -> int:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return len(doc)

def hex_to_rgb(h: Optional[str]):
    if not h:
        return None
    h = h.lstrip("#")  # รับเฉพาะ #RRGGBB
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

def resolve_font(font_filename: Optional[str]):
    """คืน (fontname_tag, full_path) จากไฟล์ใน fonts/; ถ้าไม่เจอคืน (None, None)"""
    if not font_filename:
        return None, None
    path = os.path.join("fonts", font_filename)
    if not os.path.isfile(path):
        return None, None
    tag = os.path.splitext(os.path.basename(path))[0]
    return tag, path

def apply_annotations_to_pdf(
    src_pdf: bytes,
    annotations: Dict[int, List[Dict[str, Any]]],
    disp_sizes: Dict[int, tuple],
    selected_font_filename: Optional[str]
) -> bytes:
    """รวม annotation กลับเข้า PDF โดยแมปพิกัดจากขนาดแสดงผล (disp_sizes) → ขนาดหน้าจริง"""
    doc = fitz.open(stream=src_pdf, filetype="pdf")
    out = io.BytesIO()

    font_tag, font_path = resolve_font(selected_font_filename)
    if font_tag and font_path:
        doc.insert_font(fontname=font_tag, fontfile=font_path)

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_w, page_h = page.rect.width, page.rect.height

        items = annotations.get(page_index, [])
        if not items:
            continue

        disp_w, disp_h = disp_sizes.get(page_index, (page_w, page_h))
        sx, sy = page_w / disp_w, page_h / disp_h

        for item in items:
            t = item.get("type")
            props = item.get("props", {})
            stroke = props.get("stroke", "#000000")
            fill = props.get("fill", None)  # ถ้าโปร่งใสจะเป็น None
            line_w = float(props.get("strokeWidth", 2))

            if t in ("rect", "ellipse"):
                left  = float(props.get("left", 0))   * sx
                top   = float(props.get("top", 0))    * sy
                width = float(props.get("width", 0))  * sx
                height= float(props.get("height", 0)) * sy
                rect = fitz.Rect(left, top, left+width, top+height)
                if t == "rect":
                    page.draw_rect(
                        rect,
                        color=hex_to_rgb(stroke),
                        fill=hex_to_rgb(fill) if fill else None,
                        width=line_w
                    )
                else:
                    page.draw_oval(
                        rect,
                        color=hex_to_rgb(stroke),
                        fill=hex_to_rgb(fill) if fill else None,
                        width=line_w
                    )

            elif t == "path":
                pts = [(float(p[1])*sx, float(p[2])*sy) for p in props.get("path", [])]
                if len(pts) >= 2:
                    page.draw_polyline(pts, color=hex_to_rgb(stroke), width=line_w)

            elif t == "line":
                x1 = float(props.get("x1", 0)) * sx
                y1 = float(props.get("y1", 0)) * sy
                x2 = float(props.get("x2", 0)) * sx
                y2 = float(props.get("y2", 0)) * sy
                page.draw_line(fitz.Point(x1, y1), fitz.Point(x2, y2),
                               color=hex_to_rgb(stroke), width=line_w)

            elif t == "text":
                txt  = props.get("text", "")
                if not txt:
                    continue
                left = float(props.get("left", 0)) * sx
                top  = float(props.get("top", 0))  * sy
                size = float(props.get("fontSize", 14))
                kwargs = dict(fontsize=size, color=hex_to_rgb(stroke))
                if font_tag:
                    kwargs["fontname"] = font_tag
                page.insert_text(fitz.Point(left, top + size), txt, **kwargs)

    doc.save(out)
    doc.close()
    return out.getvalue()

# ---------------- State ----------------
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "page_index" not in st.session_state:
    st.session_state.page_index = 0
if "annos" not in st.session_state:
    st.session_state.annos = {}
if "disp_sizes" not in st.session_state:
    st.session_state.disp_sizes = {}

# ---------------- Sidebar ----------------
zoom = st.sidebar.slider("ซูมหน้ากระดาษ (%)", 50, 200, 120)
stroke_width = st.sidebar.slider("ความหนาเส้น", 1, 12, 3)
stroke_color = st.sidebar.color_picker("สีเส้น/ข้อความ", "#111827")

# เลือกโปร่งใส/ไม่โปร่งใส โดยไม่ส่ง None เข้า canvas
use_fill = st.sidebar.checkbox("เติมสีพื้น (ไม่โปร่งใส)", value=False)
if use_fill:
    fill_color = st.sidebar.color_picker("เลือกสีพื้น", "#000000")
    canvas_fill = fill_color  # #RRGGBB
else:
    fill_color = None
    canvas_fill = "rgba(0,0,0,0)"  # โปร่งใส (string)

font_size = st.sidebar.slider("ขนาดตัวอักษร", 10, 72, 20)
dpi = st.sidebar.slider("DPI เรนเดอร์", 96, 200, 120)

fonts = list_fonts("fonts")
selected_font = st.sidebar.selectbox("เลือกฟอนต์จาก fonts/", ["(default)"] + fonts)
chosen_font = selected_font if selected_font != "(default)" else None

# ---------------- Upload ----------------
uploaded = st.file_uploader("อัปโหลด PDF", type="pdf")
if uploaded:
    st.session_state.pdf_bytes = uploaded.read()
    st.session_state.page_index = 0
    st.session_state.n_pages = get_page_count(st.session_state.pdf_bytes)
    for i in range(st.session_state.n_pages):
        st.session_state.annos.setdefault(i, [])

if not st.session_state.pdf_bytes:
    st.info("อัปโหลดไฟล์เพื่อเริ่มใช้งาน")
    st.stop()

# ---------------- Pager ----------------
c1, c2, c3, c4 = st.columns([2, 2, 2, 6])
with c1:
    page_i = st.number_input("หน้า", 1, st.session_state.n_pages, st.session_state.page_index + 1)
    st.session_state.page_index = page_i - 1
with c2:
    if st.button("ล้างหน้านี้", use_container_width=True):
        st.session_state.annos[st.session_state.page_index] = []
with c3:
    if st.button("บันทึกเป็น PDF", type="primary", use_container_width=True):
        pdf_out = apply_annotations_to_pdf(
            st.session_state.pdf_bytes,
            st.session_state.annos,
            st.session_state.disp_sizes,
            selected_font_filename=chosen_font
        )
        st.download_button("ดาวน์โหลด", pdf_out, "edited.pdf", "application/pdf", use_container_width=True)

# ---------------- Canvas ----------------
img = render_page_image(st.session_state.pdf_bytes, st.session_state.page_index, dpi)
disp_w, disp_h = int(img.size[0] * (zoom / 100)), int(img.size[1] * (zoom / 100))
img_disp = img.resize((disp_w, disp_h))
st.session_state.disp_sizes[st.session_state.page_index] = (disp_w, disp_h)

mode = st.radio("โหมด", ["เส้น", "สี่เหลี่ยม", "วงรี", "เส้นตรง", "ข้อความ", "ลบ"], horizontal=True)
mapping = {
    "เส้น": "freedraw",
    "สี่เหลี่ยม": "rect",
    "วงรี": "ellipse",
    "เส้นตรง": "line",
    "ข้อความ": "text",
    "ลบ": "transform",
}

json_data = st_canvas(
    fill_color=canvas_fill,                # << สำคัญ: ส่ง string เสมอ
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_image=img_disp,
    update_streamlit=True,
    height=disp_h,
    width=disp_w,
    drawing_mode=mapping[mode],
    key=f"canvas_{st.session_state.page_index}",
    font_size=font_size,
    initial_drawing={"version": "5.2.4", "objects": st.session_state.annos.get(st.session_state.page_index, [])},
    display_toolbar=True,
    background_color="rgba(0,0,0,0)"
)

if json_data and "objects" in json_data:
    st.session_state.annos[st.session_state.page_index] = json_data["objects"]
