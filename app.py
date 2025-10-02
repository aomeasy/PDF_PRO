import streamlit as st
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import os
import tempfile
import zipfile

# Import font module with error handling
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
    FONTS_AVAILABLE = True
except ImportError:
    FONTS_AVAILABLE = False

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="PDF Manager Pro",
    page_icon="📄",
    layout="wide"
)

# CSS สำหรับตกแต่ง
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 5px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ฟังก์ชันสำหรับรวม PDF
def merge_pdfs(pdf_files):
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output

# ฟังก์ชันสำหรับแบ่ง PDF
def split_pdf(pdf_file, page_ranges):
    reader = PdfReader(pdf_file)
    outputs = []
    
    for i, page_range in enumerate(page_ranges):
        writer = PdfWriter()
        start, end = page_range
        
        for page_num in range(start - 1, min(end, len(reader.pages))):
            writer.add_page(reader.pages[page_num])
        
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        outputs.append((f"split_{i+1}.pdf", output))
    
    return outputs

# ฟังก์ชันสำหรับตัดหน้า PDF
def extract_pages(pdf_file, pages_to_extract):
    reader = PdfReader(pdf_file)
    writer = PdfWriter()
    
    for page_num in pages_to_extract:
        if 0 < page_num <= len(reader.pages):
            writer.add_page(reader.pages[page_num - 1])
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# ฟังก์ชันสำหรับสร้าง PDF ใหม่พร้อมข้อความและรูปภาพ
def create_pdf_with_content(text, font_name, font_size, image=None, image_position=None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # ลงทะเบียนฟอนต์ (ต้องมีไฟล์ฟอนต์)
    try:
        if font_name == "TH Sarabun PSK":
            pdfmetrics.registerFont(TTFont('THSarabunPSK', 'fonts/THSarabunPSK.ttf'))
            c.setFont('THSarabunPSK', font_size)
        elif font_name == "TH Sarabun New":
            pdfmetrics.registerFont(TTFont('THSarabunNew', 'fonts/THSarabunNew.ttf'))
            c.setFont('THSarabunNew', font_size)
        else:
            c.setFont('Helvetica', font_size)
    except:
        c.setFont('Helvetica', font_size)
        st.warning("ไม่พบไฟล์ฟอนต์ ใช้ฟอนต์เริ่มต้นแทน")
    
    # เขียนข้อความ
    text_object = c.beginText(50, height - 100)
    for line in text.split('\n'):
        text_object.textLine(line)
    c.drawText(text_object)
    
    # เพิ่มรูปภาพ
    if image is not None:
        img = Image.open(image)
        img_width, img_height = img.size
        
        # ปรับขนาดรูปภาพ
        max_width = 400
        max_height = 400
        ratio = min(max_width/img_width, max_height/img_height)
        new_width = img_width * ratio
        new_height = img_height * ratio
        
        if image_position:
            x, y = image_position
        else:
            x, y = 50, height - 300
        
        c.drawImage(ImageReader(image), x, y - new_height, 
                   width=new_width, height=new_height)
    
    c.save()
    buffer.seek(0)
    return buffer

# ฟังก์ชันสำหรับหมุน PDF
def rotate_pdf(pdf_file, rotation_angle):
    reader = PdfReader(pdf_file)
    writer = PdfWriter()
    
    for page in reader.pages:
        page.rotate(rotation_angle)
        writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# ฟังก์ชันสำหรับลบหน้า PDF
def delete_pages(pdf_file, pages_to_delete):
    reader = PdfReader(pdf_file)
    writer = PdfWriter()
    
    for i, page in enumerate(reader.pages, 1):
        if i not in pages_to_delete:
            writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# Header
st.title("📄 PDF Manager Pro")
st.markdown("### จัดการไฟล์ PDF ได้ทุกอย่างในที่เดียว")

# Sidebar สำหรับเลือกฟีเจอร์
st.sidebar.title("เลือกฟังก์ชัน")
feature = st.sidebar.radio(
    "คุณต้องการทำอะไร?",
    ["🔗 รวมไฟล์ PDF", "✂️ แบ่งไฟล์ PDF", "📋 ตัดหน้า PDF", 
     "📝 สร้าง PDF ใหม่", "🔄 หมุน PDF", "🗑️ ลบหน้า PDF"]
)

# 1. รวมไฟล์ PDF
if feature == "🔗 รวมไฟล์ PDF":
    st.header("รวมหลาย PDF เป็นไฟล์เดียว")
    uploaded_files = st.file_uploader(
        "อัปโหลดไฟล์ PDF (สามารถเลือกหลายไฟล์)",
        type="pdf",
        accept_multiple_files=True,
        key="merge"
    )
    
    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"เลือก {len(uploaded_files)} ไฟล์")
        
        if st.button("รวมไฟล์"):
            with st.spinner("กำลังรวมไฟล์..."):
                merged_pdf = merge_pdfs(uploaded_files)
                st.success("✅ รวมไฟล์สำเร็จ!")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ที่รวมแล้ว",
                    data=merged_pdf,
                    file_name="merged.pdf",
                    mime="application/pdf"
                )

# 2. แบ่งไฟล์ PDF
elif feature == "✂️ แบ่งไฟล์ PDF":
    st.header("แบ่ง PDF ตามช่วงหน้า")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="split")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        st.info(f"ไฟล์นี้มี {total_pages} หน้า")
        
        num_splits = st.number_input("แบ่งเป็นกี่ส่วน?", min_value=1, max_value=10, value=2)
        
        page_ranges = []
        cols = st.columns(num_splits)
        for i in range(num_splits):
            with cols[i]:
                st.write(f"**ส่วนที่ {i+1}**")
                start = st.number_input(f"หน้าเริ่มต้น", min_value=1, max_value=total_pages, value=1, key=f"start_{i}")
                end = st.number_input(f"หน้าสุดท้าย", min_value=1, max_value=total_pages, value=total_pages, key=f"end_{i}")
                page_ranges.append((start, end))
        
        if st.button("แบ่งไฟล์"):
            with st.spinner("กำลังแบ่งไฟล์..."):
                split_files = split_pdf(uploaded_file, page_ranges)
                
                # สร้าง ZIP file
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, file_data in split_files:
                        zip_file.writestr(filename, file_data.read())
                
                zip_buffer.seek(0)
                st.success("✅ แบ่งไฟล์สำเร็จ!")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ทั้งหมด (ZIP)",
                    data=zip_buffer,
                    file_name="split_pdfs.zip",
                    mime="application/zip"
                )

# 3. ตัดหน้า PDF
elif feature == "📋 ตัดหน้า PDF":
    st.header("เลือกหน้าที่ต้องการจาก PDF")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="extract")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        st.info(f"ไฟล์นี้มี {total_pages} หน้า")
        
        pages_input = st.text_input(
            "ระบุหน้าที่ต้องการ (เช่น 1,3,5-7)",
            help="ใช้เครื่องหมายจุลภาค (,) สำหรับหน้าแยก และขีด (-) สำหรับช่วง"
        )
        
        if pages_input and st.button("ตัดหน้า"):
            try:
                pages_to_extract = []
                for part in pages_input.split(','):
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pages_to_extract.extend(range(start, end + 1))
                    else:
                        pages_to_extract.append(int(part.strip()))
                
                with st.spinner("กำลังตัดหน้า..."):
                    extracted_pdf = extract_pages(uploaded_file, pages_to_extract)
                    st.success(f"✅ ตัดหน้า {len(pages_to_extract)} หน้าสำเร็จ!")
                    st.download_button(
                        label="📥 ดาวน์โหลดไฟล์ที่ตัดแล้ว",
                        data=extracted_pdf,
                        file_name="extracted.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {str(e)}")

# 4. สร้าง PDF ใหม่
elif feature == "📝 สร้าง PDF ใหม่":
    st.header("สร้าง PDF พร้อมข้อความและรูปภาพ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        text_content = st.text_area(
            "เนื้อหาข้อความ",
            height=200,
            placeholder="พิมพ์ข้อความที่ต้องการใส่ใน PDF..."
        )
        
        font_choice = st.selectbox(
            "เลือกฟอนต์",
            ["Helvetica", "TH Sarabun PSK", "TH Sarabun New"]
        )
        
        font_size = st.slider("ขนาดตัวอักษร", 10, 40, 16)
    
    with col2:
        uploaded_image = st.file_uploader(
            "อัปโหลดรูปภาพ (ไม่บังคับ)",
            type=['png', 'jpg', 'jpeg'],
            key="create_image"
        )
        
        if uploaded_image:
            st.image(uploaded_image, caption="ภาพที่อัปโหลด", width=300)
            
            img_x = st.number_input("ตำแหน่ง X ของรูป", value=50)
            img_y = st.number_input("ตำแหน่ง Y ของรูป", value=500)
            image_position = (img_x, img_y)
        else:
            image_position = None
    
    if st.button("สร้าง PDF"):
        if text_content or uploaded_image:
            with st.spinner("กำลังสร้าง PDF..."):
                pdf_output = create_pdf_with_content(
                    text_content,
                    font_choice,
                    font_size,
                    uploaded_image,
                    image_position
                )
                st.success("✅ สร้าง PDF สำเร็จ!")
                st.download_button(
                    label="📥 ดาวน์โหลด PDF",
                    data=pdf_output,
                    file_name="new_document.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("กรุณาใส่ข้อความหรือรูปภาพอย่างน้อย 1 อย่าง")

# 5. หมุน PDF
elif feature == "🔄 หมุน PDF":
    st.header("หมุนหน้า PDF")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="rotate")
    
    if uploaded_file:
        rotation = st.selectbox(
            "เลือกมุมการหมุน",
            [90, 180, 270],
            format_func=lambda x: f"{x}° (หมุนตามเข็มนาฬิกา)"
        )
        
        if st.button("หมุนไฟล์"):
            with st.spinner("กำลังหมุนไฟล์..."):
                rotated_pdf = rotate_pdf(uploaded_file, rotation)
                st.success("✅ หมุนไฟล์สำเร็จ!")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ที่หมุนแล้ว",
                    data=rotated_pdf,
                    file_name="rotated.pdf",
                    mime="application/pdf"
                )

# 6. ลบหน้า PDF
elif feature == "🗑️ ลบหน้า PDF":
    st.header("ลบหน้าที่ไม่ต้องการออกจาก PDF")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="delete")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        st.info(f"ไฟล์นี้มี {total_pages} หน้า")
        
        pages_to_delete_input = st.text_input(
            "ระบุหน้าที่ต้องการลบ (เช่น 2,4,6-8)",
            help="ใช้เครื่องหมายจุลภาค (,) สำหรับหน้าแยก และขีด (-) สำหรับช่วง"
        )
        
        if pages_to_delete_input and st.button("ลบหน้า"):
            try:
                pages_to_delete = []
                for part in pages_to_delete_input.split(','):
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pages_to_delete.extend(range(start, end + 1))
                    else:
                        pages_to_delete.append(int(part.strip()))
                
                with st.spinner("กำลังลบหน้า..."):
                    result_pdf = delete_pages(uploaded_file, pages_to_delete)
                    remaining_pages = total_pages - len(pages_to_delete)
                    st.success(f"✅ ลบ {len(pages_to_delete)} หน้าสำเร็จ! เหลือ {remaining_pages} หน้า")
                    st.download_button(
                        label="📥 ดาวน์โหลดไฟล์ที่ลบหน้าแล้ว",
                        data=result_pdf,
                        file_name="deleted_pages.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>พัฒนาด้วย ❤️ โดยใช้ Streamlit | © 2025 PDF Manager Pro</p>
    </div>
    """,
    unsafe_allow_html=True
)
