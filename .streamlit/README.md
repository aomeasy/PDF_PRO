# 📄 PDF Manager Pro

เว็บแอปพลิเคชันสำหรับจัดการไฟล์ PDF อย่างครบครัน พัฒนาด้วย Python และ Streamlit รองรับฟอนต์ภาษาไทย

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31.0-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ ฟีเจอร์หลัก

### 🔗 รวมไฟล์ PDF
- รวมหลายไฟล์ PDF เป็นไฟล์เดียว
- รองรับการอัปโหลดหลายไฟล์พร้อมกัน
- ดาวน์โหลดไฟล์ที่รวมแล้วได้ทันที

### ✂️ แบ่งไฟล์ PDF
- แบ่ง PDF ออกเป็นหลายส่วนตามช่วงหน้าที่กำหนด
- กำหนดจำนวนส่วนและช่วงหน้าได้เอง
- ดาวน์โหลดเป็นไฟล์ ZIP

### 📋 ตัดหน้า PDF
- เลือกหน้าที่ต้องการจาก PDF
- รองรับการเลือกหน้าแยก (1,3,5) และช่วง (5-10)
- สร้างไฟล์ PDF ใหม่ที่มีเฉพาะหน้าที่เลือก

### 📝 สร้าง PDF ใหม่
- สร้าง PDF พร้อมข้อความภาษาไทย
- รองรับฟอนต์ TH Sarabun PSK และ TH Sarabun New
- แทรกรูปภาพได้
- ปรับขนาดฟอนต์และตำแหน่งรูปภาพได้

### 🔄 หมุน PDF
- หมุนทุกหน้าใน PDF
- รองรับมุม 90°, 180°, 270°

### 🗑️ ลบหน้า PDF
- ลบหน้าที่ไม่ต้องการออกจาก PDF
- รองรับการลบหลายหน้าพร้อมกัน

## 🚀 วิธีการติดตั้งและใช้งาน

### ติดตั้งในเครื่องของคุณ

1. **Clone repository**
```bash
git clone https://github.com/yourusername/pdf-manager-pro.git
cd pdf-manager-pro
```

2. **สร้าง Virtual Environment (แนะนำ)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **ติดตั้ง Dependencies**
```bash
pip install -r requirements.txt
```

4. **เพิ่มไฟล์ฟอนต์ (สำหรับภาษาไทย)**
```
สร้างโฟลเดอร์ fonts/ และใส่ไฟล์:
- THSarabunPSK.ttf
- THSarabunNew.ttf
```

5. **รันแอปพลิเคชัน**
```bash
streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501`

### 🌐 Deploy บน Streamlit Cloud

1. **Push โค้ดขึ้น GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Deploy ผ่าน Streamlit Cloud**
- ไปที่ [share.streamlit.io](https://share.streamlit.io)
- เข้าสู่ระบบด้วย GitHub
- คลิก "New app"
- เลือก repository, branch, และไฟล์ `app.py`
- คลิก "Deploy"

3. **ตั้งค่าเพิ่มเติม (ถ้าต้องการใช้ฟอนต์ไทย)**
- อัปโหลดไฟล์ฟอนต์ลงใน GitHub
- หรือใช้ packages.txt สำหรับติดตั้งฟอนต์

## 📁 โครงสร้างโปรเจค

```
pdf-manager-pro/
│
├── app.py                    # ไฟล์หลักของแอปพลิเคชัน
├── requirements.txt          # Python dependencies
├── README.md                 # เอกสารนี้
│
├── .streamlit/
│   └── config.toml          # การตั้งค่า Streamlit
│
├── fonts/                    # โฟลเดอร์สำหรับไฟล์ฟอนต์ (ต้องสร้างเอง)
│   ├── THSarabunPSK.ttf
│   └── THSarabunNew.ttf
│
└── .gitignore               # ไฟล์ที่ไม่ต้องการใน Git
```

## 🛠️ เทคโนโลยีที่ใช้

- **Streamlit** - Web framework สำหรับ Python
- **PyPDF2** - จัดการไฟล์ PDF
- **ReportLab** - สร้าง PDF ใหม่
- **Pillow** - ประมวลผลรูปภาพ

## 📋 ข้อกำหนดระบบ

- Python 3.9 หรือสูงกว่า
- RAM อย่างน้อย 2GB
- พื้นที่ว่างในฮาร์ดดิสก์ 100MB

## 🔒 ความปลอดภัย

- ไฟล์ทั้งหมดประมวลผลในหน่วยความจำ
- ไม่มีการเก็บไฟล์บนเซิร์ฟเวอร์
- ข้อมูลจะถูกลบทันทีหลังจากดาวน์โหลด

## 💡 เคล็ดลับการใช้งาน

1. **การรวมไฟล์**: ลากไฟล์ในลำดับที่ต้องการก่อนรวม
2. **การแบ่งไฟล์**: ตรวจสอบจำนวนหน้าก่อนกำหนดช่วง
3. **ฟอนต์ภาษาไทย**: ต้องมีไฟล์ .ttf ในโฟลเดอร์ fonts/
4. **รูปภาพ**: รองรับ PNG, JPG, JPEG

## 🐛 การแก้ไขปัญหา

### ฟอนต์ภาษาไทยไม่แสดง
```bash
# ตรวจสอบว่ามีไฟล์ฟอนต์ใน fonts/
ls fonts/

# หรือดาวน์โหลดฟอนต์ฟรีจาก
# https://www.f0nt.com/release/th-sarabun-new/
```

### Error: Module not found
```bash
# อัปเดต pip และติดตั้ง requirements ใหม่
pip install --upgrade pip
pip install -r requirements.txt
```

### Streamlit Cloud ไม่ทำงาน
- ตรวจสอบว่า requirements.txt อยู่ใน root directory
- ตรวจสอบ Python version ใน Streamlit Cloud settings

## 📝 License

MIT License - ใช้งานได้อย่างอิสระ

## 🤝 การมีส่วนร่วม

ยินดีรับ Pull Requests และ Issues ทุกรูปแบบ!

1. Fork โปรเจค
2. สร้าง Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit การเปลี่ยนแปลง (`git commit -m 'Add some AmazingFeature'`)
4. Push ไปยัง Branch (`git push origin feature/AmazingFeature`)
5. เปิด Pull Request

## 👨‍💻 ผู้พัฒนา

สร้างด้วย ❤️ โดยใช้ Streamlit

## 📞 ติดต่อ

- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

## 🙏 ขอบคุณ

- [Streamlit](https://streamlit.io/) - สำหรับ web framework ที่ยอดเยี่ยม
- [PyPDF2](https://pypdf2.readthedocs.io/) - สำหรับการจัดการ PDF
- [ReportLab](https://www.reportlab.com/) - สำหรับการสร้าง PDF

---

⭐ ถ้าชอบโปรเจคนี้ กด Star ให้หน่อยนะ!
