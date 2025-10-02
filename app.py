import streamlit as st
import streamlit.components.v1 as components
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image
import io
import json
import base64
import os

# Import font module with error handling
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
    FONTS_AVAILABLE = True
except ImportError:
    FONTS_AVAILABLE = False

# -----------------------------------------------------------------------------
# Page config & global CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="PDF Manager Pro - Interactive", page_icon="📄", layout="wide")

st.markdown("""
<style>
/* Modern look */
:root{
  --pri:#6c63ff; --pri2:#764ba2; --ok:#22c55e; --warn:#ef4444; --muted:#6b7280;
}
html, body { background: #f6f7fb; }
.block-container { padding-top: 1rem; }

/* Header card */
.app-header{
  background: linear-gradient(135deg, var(--pri) 0%, var(--pri2) 100%);
  color: #fff; padding: 20px 24px; border-radius: 16px;
  box-shadow: 0 8px 24px rgba(108,99,255,.25);
  margin-bottom: 16px;
}
.app-header h1{ margin:0; font-size: 1.4rem; font-weight: 700; }
.app-header p{ margin:6px 0 0; opacity:.95 }

/* Sticky action bar */
.sticky-actions{
  position: sticky; top: 0; z-index: 50; padding: 10px 0 0; margin-top: 6px;
}
.action-bar{
  background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:10px;
  box-shadow: 0 6px 18px rgba(0,0,0,.06);
  display:flex;gap:10px; align-items:center; justify-content:space-between;
}
.action-left{ display:flex; gap:10px; align-items:center; }
.action-right{ display:flex; gap:8px; }

/* Buttons */
.btn{
  border:none; border-radius:10px; font-weight:700; cursor:pointer; padding:10px 14px;
}
.btn-primary{ background:var(--pri); color:#fff; }
.btn-success{ background:var(--ok); color:#fff; }
.btn-danger{ background:var(--warn); color:#fff; }
.btn-ghost{ background:#f3f4f6; color:#111827; }
.btn:disabled{ opacity:.6; cursor:not-allowed; }

/* Cards */
.card{
  background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:16px;
  box-shadow:0 6px 18px rgba(0,0,0,.06);
}

/* Editor container label */
.section-title{ font-weight:800; font-size:1.05rem; color:#111827; margin-bottom:8px; }

/* Make Streamlit widgets a bit tighter */
.css-1kyxreq, .stButton button{ border-radius:12px!important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Core: build final PDF from bytes + elements
# -----------------------------------------------------------------------------
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    """สร้าง PDF ใหม่โดยเพิ่ม text overlay (ใช้ A4: 595x842)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4

    # group by page
    elements_by_page = {}
    for element in text_elements:
        page_idx = int(element.get('page', 1))
        elements_by_page.setdefault(page_idx, []).append(element)

    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in elements_by_page:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)

            for el in elements_by_page[page_num]:
                text = el.get('text', '')
                x = float(el.get('x', 50))
                y = float(el.get('y', 700))
                font_size = int(el.get('fontSize', 16))
                font_name = el.get('font', 'Helvetica')
                color = el.get('color', '#000000')
                # hex -> rgb
                try:
                    c = color.lstrip('#')
                    r, g, b = (int(c[i:i+2], 16)/255 for i in (0,2,4))
                except Exception:
                    r=g=b=0
                can.setFillColorRGB(r,g,b)

                try:
                    if font_name in ["THSarabunPSK", "THSarabunNew"] and FONTS_AVAILABLE:
                        font_path = f"fonts/{font_name}.ttf"
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            can.setFont(font_name, font_size)
                        else:
                            can.setFont('Helvetica', font_size)
                    else:
                        can.setFont(font_name, font_size)
                except Exception:
                    can.setFont('Helvetica', font_size)

                y_pdf = height - y - font_size
                can.drawString(x, y_pdf, text)

            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            page.merge_page(overlay_pdf.pages[0])

        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out

# -----------------------------------------------------------------------------
# Interactive PDF Editor (returns elements via postMessage -> Streamlit)
# -----------------------------------------------------------------------------
def interactive_pdf_editor(pdf_bytes: bytes | None = None):
    """ฝัง editor และคืนค่า textElements ถ้ากด 'บันทึกลงแอป' """
    pdf_base64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

    # embed custom fonts if present for preview
    custom_font_css = ""
    for fname in ["THSarabunPSK", "THSarabunNew"]:
        fpath = os.path.join("fonts", f"{fname}.ttf")
        if os.path.exists(fpath):
            try:
                with open(fpath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                custom_font_css += f"""
                @font-face {{
                    font-family: '{fname}';
                    src: url(data:font/ttf;base64,{b64}) format('truetype');
                    font-weight: normal; font-style: normal; font-display: swap;
                }}
                """
            except Exception:
                pass

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            {custom_font_css}
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family:'Sarabun','Noto Sans Thai',Tahoma,sans-serif; }}
            .toolbar {{
                background: linear-gradient(135deg,#6c63ff 0%,#764ba2 100%);
                padding: 16px; border-radius: 14px; color:#fff;
            }}
            .toolbar h3 {{ margin-bottom:10px; }}
            .controls {{
                display:grid; grid-template-columns: 2fr 120px 120px; gap:10px;
                margin-top:8px;
            }}
            .controls textarea, .controls select, .controls input[type="number"], .controls input[type="color"] {{
                border:none; border-radius:10px; padding:10px; font-size:14px;
            }}
            .controls textarea {{ grid-column: 1 / 4; min-height:60px; resize:vertical; }}
            .btn {{ padding:10px 14px; border:none; border-radius:10px; font-weight:700; cursor:pointer; }}
            .btn-ghost{{ background:#f3f4f6; }}
            .btn-save{{ background:#22c55e; color:#fff; }}
            .btn-clear{{ background:#ef4444; color:#fff; }}
            .canvas-wrap{{ padding:18px; }}
            #canvas{{ width:595px;height:842px;border:2px solid #e5e7eb;margin:0 auto;position:relative;background:#fff;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.06); }}
            #pdfCanvas{{ position:absolute;top:0;left:0;width:595px;height:842px;pointer-events:none; }}
            .text-element{{ position:absolute; cursor:move; padding:4px 6px; border:2px dashed transparent; user-select:none; white-space:pre-wrap; z-index:10; }}
            .text-element:hover{{ border-color:#6c63ff; background:rgba(108,99,255,.08); }}
            .text-element.selected{{ border-color:#6c63ff; background:rgba(108,99,255,.12); }}
            .delete-btn {{ position:absolute; top:-12px; right:-12px; width:24px; height:24px; background:#ef4444; color:#fff; border:none; border-radius:50%; cursor:pointer; display:none; }}
            .text-element:hover .delete-btn{{ display:block; }}
            .resize-handle {{ position:absolute; bottom:-5px; right:-5px; width:12px; height:12px; background:#6c63ff; border-radius:50%; cursor:nwse-resize; display:none; }}
            .text-element:hover .resize-handle{{ display:block; }}
            .row {{ display:flex; gap:10px; margin-top:10px; }}
        </style>
    </head>
    <body>
        <div class="toolbar">
            <h3>🎨 PDF Interactive Editor</h3>
            <div class="controls">
                <textarea id="textInput" placeholder="พิมพ์ข้อความที่ต้องการเพิ่ม..."></textarea>
                <select id="fontSelect">
                    <option value="Helvetica">Helvetica</option>
                    <option value="Times-Roman">Times New Roman</option>
                    <option value="Courier">Courier</option>
                    <option value="THSarabunPSK">TH Sarabun PSK</option>
                    <option value="THSarabunNew">TH Sarabun New</option>
                </select>
                <input type="number" id="fontSize" value="16" min="8" max="72">
                <input type="color" id="textColor" value="#111111" style="grid-column: 1 / 2;">
                <div class="row" style="justify-content:flex-end;">
                    <button class="btn btn-ghost" onclick="addText()">➕ เพิ่มข้อความ</button>
                    <button class="btn btn-clear" onclick="clearAll()">🗑️ ล้างข้อความในหน้านี้</button>
                    <button class="btn btn-save" onclick="saveToApp()">✅ บันทึกลงแอป</button>
                </div>
            </div>
        </div>

        <div class="canvas-wrap">
            <div id="canvas">
                <canvas id="pdfCanvas" width="595" height="842"></canvas>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
        <script>
            // --- helpers ---
            const CSS_FONT_MAP = {{
                "Helvetica": "Helvetica, Arial, sans-serif",
                "Times-Roman": "'Times New Roman', Times, serif",
                "Courier": "'Courier New', Courier, monospace",
                "THSarabunPSK": "'THSarabunPSK','Sarabun','Noto Sans Thai',sans-serif",
                "THSarabunNew": "'THSarabunNew','Sarabun','Noto Sans Thai',sans-serif"
            }};
            function base64ToUint8Array(base64){{
                const raw=atob(base64); const arr=new Uint8Array(raw.length);
                for(let i=0;i<raw.length;i++) arr[i]=raw.charCodeAt(i); return arr;
            }}
            function cssFontFamily(name){{ return CSS_FONT_MAP[name] || name; }}

            // state
            let textElements = [];
            let elementCounter = 0;
            let selectedElement = null, isDragging=false, isResizing=false, startX, startY, startLeft, startTop, startFontSize;

            // render page 1
            const pdfData = '{pdf_base64}';
            if(pdfData){{
                pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                const uint8=base64ToUint8Array(pdfData);
                pdfjsLib.getDocument({{data:uint8}}).promise.then(pdf=>pdf.getPage(1)).then(page=>{{
                    const c=document.getElementById('pdfCanvas'); const ctx=c.getContext('2d');
                    const unscaled=page.getViewport({{scale:1}});
                    const scale=Math.min(595/unscaled.width, 842/unscaled.height);
                    const viewport=page.getViewport({{scale}});
                    c.width=viewport.width; c.height=viewport.height;
                    return page.render({{canvasContext:ctx, viewport}}).promise;
                }}).catch(err=>console.error('pdf.js error', err));
            }}

            // add & ui handlers
            function addText(){{
                const text=document.getElementById('textInput').value.trim();
                if(!text){{ alert('กรุณาใส่ข้อความ'); return; }}
                const el={{ id:++elementCounter, text, x:50, y:50,
                    fontSize: parseInt(document.getElementById('fontSize').value)||16,
                    font: document.getElementById('fontSelect').value,
                    color: document.getElementById('textColor').value,
                    page:1 }};
                textElements.push(el); createTextDiv(el); document.getElementById('textInput').value='';
            }}
            function createTextDiv(el){{
                const wrap=document.getElementById('canvas');
                const div=document.createElement('div'); div.className='text-element'; div.id='text-'+el.id;
                Object.assign(div.style, {{ left:el.x+'px', top:el.y+'px', fontSize:el.fontSize+'px',
                                            fontFamily:cssFontFamily(el.font), color:el.color }});
                div.textContent=el.text;
                const del=document.createElement('button'); del.className='delete-btn'; del.textContent='×';
                del.onclick=e=>{{ e.stopPropagation(); deleteText(el.id); }};
                const rh=document.createElement('div'); rh.className='resize-handle';
                div.appendChild(del); div.appendChild(rh);
                div.addEventListener('mousedown', e=>startDrag(e,el));
                rh.addEventListener('mousedown', e=>startResize(e,el));
                wrap.appendChild(div);
            }}
            function startDrag(e,el){{
                if(e.target.className==='resize-handle') return;
                selectedElement=el; isDragging=true; startX=e.clientX; startY=e.clientY; startLeft=el.x; startTop=el.y;
                document.getElementById('text-'+el.id).classList.add('selected');
            }}
            function startResize(e,el){{
                e.stopPropagation(); selectedElement=el; isResizing=true; startY=e.clientY; startFontSize=el.fontSize;
            }}
            function deleteText(id){{
                textElements=textElements.filter(x=>x.id!==id);
                const div=document.getElementById('text-'+id); if(div) div.remove();
            }}
            function clearAll(){{
                if(!confirm('ลบข้อความทั้งหมดบนหน้านี้?')) return;
                textElements.forEach(x=>{{ const d=document.getElementById('text-'+x.id); if(d) d.remove(); }});
                textElements=[];
            }}

            document.addEventListener('mousemove', e=>{{
                if(isDragging && selectedElement){{
                    const dx=e.clientX-startX, dy=e.clientY-startY;
                    selectedElement.x=Math.max(0, Math.min(startLeft+dx, 550));
                    selectedElement.y=Math.max(0, Math.min(startTop+dy, 800));
                    const div=document.getElementById('text-'+selectedElement.id);
                    div.style.left=selectedElement.x+'px'; div.style.top=selectedElement.y+'px';
                }}
                if(isResizing && selectedElement){{
                    const dy=e.clientY-startY; const size=Math.max(8, Math.min(72, startFontSize+dy));
                    selectedElement.fontSize=size; document.getElementById('text-'+selectedElement.id).style.fontSize=size+'px';
                }}
            }});
            document.addEventListener('mouseup', ()=>{{
                if(selectedElement) document.getElementById('text-'+selectedElement.id).classList.remove('selected');
                isDragging=false; isResizing=false; selectedElement=null;
            }});

            // realtime style change for selected element
            document.getElementById('fontSelect').addEventListener('change', e=>{{
                if(!selectedElement) return; selectedElement.font=e.target.value;
                document.getElementById('text-'+selectedElement.id).style.fontFamily=cssFontFamily(selectedElement.font);
            }});
            document.getElementById('fontSize').addEventListener('change', e=>{{
                if(!selectedElement) return; const s=parseInt(e.target.value)||16;
                selectedElement.fontSize=s; document.getElementById('text-'+selectedElement.id).style.fontSize=s+'px';
            }});
            document.getElementById('textColor').addEventListener('change', e=>{{
                if(!selectedElement) return; selectedElement.color=e.target.value;
                document.getElementById('text-'+selectedElement.id).style.color=selectedElement.color;
            }});

            // >>> 핵심: ส่งค่า elements กลับไปยัง Streamlit
            function saveToApp(){{
                const payload = JSON.stringify(textElements);
                const msg = {{ isStreamlitMessage: true, type: "streamlit:setComponentValue", value: payload }};
                window.parent.postMessage(msg, "*");
                alert("✅ บันทึกข้อมูลลงแอปแล้ว! เลื่อนขึ้นไปที่แถบด้านบนแล้วกด 'สร้าง PDF'");
            }}
        </script>
    </body>
    </html>
    """
    # NOTE: components.html CAN return a value when we postMessage with "streamlit:setComponentValue"
    return components.html(html_code, height=900, scrolling=True)

# -----------------------------------------------------------------------------
# App layout
# -----------------------------------------------------------------------------
st.markdown('<div class="app-header"><h1>📄 PDF Manager Pro – Interactive Edition</h1><p>ลาก-วางข้อความบนหน้ากระดาษ • รองรับฟอนต์ไทย • รวมไฟล์ PDF</p></div>', unsafe_allow_html=True)

feature = st.sidebar.radio("เลือกฟังก์ชัน", ["✏️ แก้ไข PDF (Interactive)", "🔗 รวมไฟล์ PDF"])

# -----------------------------------------------------------------------------
# Interactive Editor Flow
# -----------------------------------------------------------------------------
if feature == "✏️ แก้ไข PDF (Interactive)":
    with st.container():
        uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="edit_pdf")
        if uploaded_file:
            pdf_bytes = uploaded_file.getvalue()
            reader = PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            st.success(f"✅ อัปโหลดไฟล์สำเร็จ: {uploaded_file.name}")
            st.info(f"📄 ไฟล์มี {total_pages} หน้า (ตัวอย่างจะเรนเดอร์หน้าแรก)")

            # Sticky action bar (top)
            st.markdown('<div class="sticky-actions"><div class="action-bar"><div class="action-left">🖊️ จัดวางข้อความบนเอกสาร แล้วกด “บันทึกลงแอป”</div><div class="action-right" id="top-actions"></div></div></div>', unsafe_allow_html=True)

            # --- interactive editor returns JSON when user clicks "บันทึกลงแอป"
            elements_json = interactive_pdf_editor(pdf_bytes)

            # If editor posted a value
            if elements_json is not None:
                try:
                    data = json.loads(elements_json)
                    st.session_state.text_elements = data
                    st.toast("รับข้อมูลจาก Editor แล้ว ✨", icon="✅")
                except Exception:
                    st.toast("รูปแบบข้อมูลจาก Editor ไม่ถูกต้อง", icon="⚠️")

            # Right panel actions (Create / Clear)
            col_a, col_b = st.columns([3,2])
            with col_b:
                st.markdown("#### 🚀 ดำเนินการ")
                if st.button("🎨 สร้าง PDF", type="primary", use_container_width=True,
                             disabled=not st.session_state.get('text_elements')):
                    with st.spinner("กำลังสร้าง PDF..."):
                        try:
                            edited_pdf = edit_pdf_with_elements(pdf_bytes, st.session_state.get('text_elements', []))
                            st.success("✅ สร้าง PDF สำเร็จ!")
                            st.download_button(
                                label="📥 ดาวน์โหลด PDF ที่แก้ไขแล้ว",
                                data=edited_pdf, file_name="edited_" + uploaded_file.name,
                                mime="application/pdf", use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

                if st.button("🧹 ล้างรายการข้อความ", use_container_width=True):
                    st.session_state.text_elements = []
                    st.toast("ล้างรายการแล้ว", icon="🧹")
                    st.experimental_rerun()

            # Show current elements
            with col_a:
                st.markdown("#### 🧾 รายการข้อความที่บันทึกไว้")
                elements = st.session_state.get('text_elements', [])
                if elements:
                    for i, el in enumerate(elements, 1):
                        st.write(f"**{i}.** `{el.get('text','')[:50]}` | ฟอนต์: {el.get('font')} | ขนาด: {el.get('fontSize')} | ตำแหน่ง: ({el.get('x')}, {el.get('y')}) | หน้า: {el.get('page',1)}")
                    with st.expander("ดูข้อมูล JSON"):
                        st.json(elements)
                else:
                    st.info("ยังไม่มีข้อมูลจากตัวแก้ไข — กดปุ่ม **บันทึกลงแอป** ในตัวแก้ไขด้านบนก่อน")

# -----------------------------------------------------------------------------
# Merge PDFs
# -----------------------------------------------------------------------------
elif feature == "🔗 รวมไฟล์ PDF":
    st.markdown('<div class="card"><div class="section-title">🔗 รวมหลายไฟล์ PDF เป็นไฟล์เดียว</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ PDF (หลายไฟล์)", type="pdf", accept_multiple_files=True, key="merge_files")
    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"เลือก {len(uploaded_files)} ไฟล์")
        if st.button("รวมไฟล์", type="primary"):
            with st.spinner("กำลังรวมไฟล์..."):
                merger = PdfMerger()
                for pdf in uploaded_files:
                    merger.append(io.BytesIO(pdf.getvalue()))
                output = io.BytesIO()
                merger.write(output)
                merger.close()
                output.seek(0)
                st.success("✅ รวมไฟล์สำเร็จ!")
                st.download_button("📥 ดาวน์โหลดไฟล์ที่รวมแล้ว", data=output, file_name="merged.pdf", mime="application/pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("""
<hr style="margin:28px 0; opacity:.2">
<div style='text-align:center; color:#6b7280'>
  พัฒนาด้วย ❤️ โดยใช้ Streamlit | © 2025 PDF Manager Pro - Interactive Edition
</div>
""", unsafe_allow_html=True)
