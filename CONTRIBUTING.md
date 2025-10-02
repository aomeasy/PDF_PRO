# 🤝 คู่มือการมีส่วนร่วม

ขอบคุณที่สนใจมีส่วนร่วมในโปรเจค PDF Manager Pro! 

## 🌟 วิธีการมีส่วนร่วม

### การรายงาน Bug

1. ตรวจสอบว่ามีคนรายงาน bug นี้แล้วหรือยัง
2. สร้าง Issue ใหม่พร้อมข้อมูล:
   - คำอธิบาย bug
   - ขั้นตอนการทำซ้ำ
   - ผลลัพธ์ที่คาดหวัง
   - ผลลัพธ์จริง
   - Screenshots (ถ้ามี)
   - ข้อมูลระบบ (OS, Python version)

### การเสนอฟีเจอร์ใหม่

1. สร้าง Issue พร้อมข้อมูล:
   - คำอธิบายฟีเจอร์
   - เหตุผลที่ต้องการ
   - ตัวอย่างการใช้งาน

### การส่ง Pull Request

1. **Fork Repository**
```bash
# คลิก Fork บน GitHub
```

2. **Clone และสร้าง Branch**
```bash
git clone https://github.com/YOUR_USERNAME/pdf-manager-pro.git
cd pdf-manager-pro
git checkout -b feature/amazing-feature
```

3. **พัฒนา Feature**
```bash
# เขียนโค้ด
# ทดสอบ
# Commit
git add .
git commit -m "Add: amazing feature description"
```

4. **Push และสร้าง PR**
```bash
git push origin feature/amazing-feature
# ไปที่ GitHub และสร้าง Pull Request
```

## 📋 แนวทางการเขียนโค้ด

### Python Style Guide

- ใช้ PEP 8
- ชื่อฟังก์ชันใช้ snake_case
- ชื่อ class ใช้ PascalCase
- เพิ่ม docstrings สำหรับฟังก์ชันที่ซับซ้อน

```python
def merge_pdfs(pdf_files):
    """
    รวมหลายไฟล์ PDF เป็นไฟล์เดียว
    
    Args:
        pdf_files (list): รายการไฟล์ PDF
        
    Returns:
        BytesIO: ไฟล์ PDF ที่รวมแล้ว
    """
    # โค้ด
```

### Commit Message Format

```
Type: Short description

Longer description (optional)

Examples:
- Add: เพิ่มฟีเจอร์การหมุน PDF
- Fix: แก้ไขบัคการรวมไฟล์
- Update: อัปเดต UI ให้สวยงามขึ้น
- Docs: เพิ่มคำอธิบายใน README
```

## 🧪 การทดสอบ

ก่อนส่ง PR กรุณาทดสอบ:

1. **ทดสอบ Feature ใหม่**
```bash
streamlit run app.py
# ทดสอบฟีเจอร์ทั้งหมด
```

2. **ตรวจสอบ Code Style**
```bash
pip install flake8
flake8 app.py
```

3. **ทดสอบกับไฟล์ตัวอย่าง**
- PDF ขนาดเล็ก (< 1MB)
- PDF ขนาดใหญ่ (> 10MB)
- PDF หลายหน้า
- PDF ที่มีรูปภาพ

## 💡 ไอเดียสำหรับการพัฒนา

### ฟีเจอร์ที่น่าสนใจ

- [ ] เพิ่ม Watermark ให้ PDF
- [ ] แปลง PDF เป็นรูปภาพ
- [ ] OCR สำหรับดึงข้อความจาก PDF
- [ ] เข้ารหัส/ถอดรหัส PDF
- [ ] บีบอัดขนาดไฟล์ PDF
- [ ] Preview PDF ก่อนดาวน์โหลด
- [ ] รองรับ Dark Mode
- [ ] รองรับหลายภาษา (i18n)
- [ ] Export เป็น Word/Excel
- [ ] Batch processing

### การปรับปรุง UI/UX

- [ ] Animation ตอน upload
- [ ] Progress bar สำหรับการประมวลผล
- [ ] Drag & drop ไฟล์
- [ ] Preview thumbnails
- [ ] Responsive design

### การปรับปรุงประสิทธิภาพ

- [ ] Async processing
- [ ] Caching
- [ ] Lazy loading
- [ ] Memory optimization

## 📞 ติดต่อ

หากมีคำถามเกี่ยวกับการมีส่วนร่วม:

- เปิด Issue บน GitHub
- Email: your.email@example.com

## 📜 Code of Conduct

เราคาดหวังให้ผู้มีส่วนร่วมทุกคน:

1. มีความเคารพต่อกัน
2. เปิดใจรับฟังความคิดเห็น
3. ให้ feedback ที่สร้างสรรค์
4. ไม่ใช้ภาษาที่ไม่เหมาะสม

## ⭐ ขอบคุณ

ขอบคุณทุกคนที่มีส่วนร่วมในโปรเจคนี้!

รายชื่อผู้ร่วมพัฒนา: [Contributors](https://github.com/yourusername/pdf-manager-pro/graphs/contributors)
