# 🚀 คู่มือการ Deploy PDF Manager Pro

## วิธีที่ 1: Deploy บน Streamlit Cloud (แนะนำ)

### ขั้นตอนที่ 1: เตรียม GitHub Repository

1. **สร้าง Repository ใหม่บน GitHub**
   - ไปที่ https://github.com/new
   - ตั้งชื่อ repository เช่น `pdf-manager-pro`
   - เลือก Public
   - คลิก "Create repository"

2. **Push โค้ดขึ้น GitHub**
```bash
# Initialize git (ถ้ายังไม่ได้ทำ)
git init

# เพิ่มไฟล์ทั้งหมด
git add .

# Commit
git commit -m "Initial commit: PDF Manager Pro"

# เชื่อมต่อกับ GitHub
git remote add origin https://github.com/YOUR_USERNAME/pdf-manager-pro.git

# Push
git branch -M main
git push -u origin main
```

### ขั้นตอนที่ 2: Deploy บน Streamlit Cloud

1. **เข้าสู่ Streamlit Cloud**
   - ไปที่ https://share.streamlit.io
   - คลิก "Sign in with GitHub"
   - อนุญาตให้ Streamlit เข้าถึง GitHub

2. **สร้าง App ใหม่**
   - คลิก "New app"
   - เลือก Repository: `your-username/pdf-manager-pro`
   - Branch: `main`
   - Main file path: `app.py`
   - คลิก "Deploy!"

3. **รอการ Deploy (ประมาณ 2-3 นาที)**
   - Streamlit จะติดตั้ง dependencies อัตโนมัติ
   - เมื่อเสร็จจะได้ URL เช่น `https://pdf-manager-pro.streamlit.app`

### ขั้นตอนที่ 3: เพิ่มฟอนต์ไทย (Optional)

**วิธีที่ 1: อัปโหลดฟอนต์ลง GitHub**
```bash
# สร้างโฟลเดอร์ fonts และใส่ไฟล์ .ttf
mkdir -p fonts
# คัดลอกไฟล์ฟอนต์เข้าไป
cp /path/to/THSarabunPSK.ttf fonts/
cp /path/to/THSarabunNew.ttf fonts/

# Push ขึ้น GitHub
git add fonts/
git commit -m "Add Thai fonts"
git push
```

**วิธีที่ 2: ใช้ System Fonts**
- ไฟล์ `packages.txt` จะติดตั้งฟอนต์ไทยจากระบบอัตโนมัติ

---

## วิธีที่ 2: Deploy บน Heroku

### ขั้นตอนที่ 1: เตรียมไฟล์

1. **สร้างไฟล์ `Procfile`**
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

2. **สร้างไฟล์ `runtime.txt`**
```
python-3.9.18
```

### ขั้นตอนที่ 2: Deploy

```bash
# Login Heroku
heroku login

# สร้าง app
heroku create pdf-manager-pro

# Deploy
git push heroku main

# เปิดแอป
heroku open
```

---

## วิธีที่ 3: Deploy บน Google Cloud Run

### ขั้นตอนที่ 1: สร้าง Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fonts-thai-tlwg \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt .
COPY app.py .
COPY .streamlit .streamlit
COPY fonts fonts

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run app
CMD streamlit run app.py --server.port=8080 --server.address=0.0.0.0
```

### ขั้นตอนที่ 2: Build และ Deploy

```bash
# Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/pdf-manager

# Deploy
gcloud run deploy pdf-manager \
  --image gcr.io/PROJECT_ID/pdf-manager \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated
```

---

## วิธีที่ 4: Deploy บน AWS (EC2)

### ขั้นตอนที่ 1: เชื่อมต่อ EC2

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### ขั้นตอนที่ 2: ติดตั้ง

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3-pip python3-venv -y

# Clone repository
git clone https://github.com/YOUR_USERNAME/pdf-manager-pro.git
cd pdf-manager-pro

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with nohup
nohup streamlit run app.py --server.port=8501 &
```

### ขั้นตอนที่ 3: ตั้งค่า Nginx (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## การตั้งค่าเพิ่มเติม

### ตั้งค่า Custom Domain

**Streamlit Cloud:**
1. ไปที่ App settings
2. คลิก "Custom domain"
3. เพิ่ม CNAME record: `your-domain.com` → `your-app.streamlit.app`

### ตั้งค่า Environment Variables

สร้างไฟล์ `.streamlit/secrets.toml` (สำหรับ local):
```toml
# API Keys หรือค่าอื่นๆ
api_key = "your-secret-key"
```

บน Streamlit Cloud:
1. ไปที่ App settings
2. คลิก "Secrets"
3. เพิ่มค่าที่ต้องการ

---

## การแก้ไขปัญหา Deployment

### ปัญหา: Build ล้มเหลว
```bash
# ตรวจสอบ requirements.txt
cat requirements.txt

# ตรวจสอบ Python version
python --version
```

### ปัญหา: ฟอนต์ไม่แสดง
- ตรวจสอบว่ามีไฟล์ในโฟลเดอร์ `fonts/`
- ตรวจสอบว่า `packages.txt` มีการติดตั้งฟอนต์

### ปัญหา: Memory Error
- เพิ่ม memory limit ใน Streamlit Cloud settings
- หรือเปลี่ยนไปใช้ Heroku/Cloud Run

---

## เคล็ดลับ

1. **ใช้ Streamlit Cloud สำหรับโปรเจคเล็ก** - ฟรีและง่ายที่สุด
2. **ใช้ Heroku สำหรับโปรเจคกลาง** - Flexible มากขึ้น
3. **ใช้ GCP/AWS สำหรับ Production** - Scalable และมี features เยอะ

4. **ปรับปรุงประสิทธิภาพ:**
   - ใช้ `@st.cache_data` สำหรับฟังก์ชันที่ต้องการ cache
   - จำกัดขนาดไฟล์ที่อัปโหลด
   - ใช้ session state สำหรับเก็บข้อมูล

---

## ลิงก์ที่เป็นประโยชน์

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Heroku Python Guide](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Google Cloud Run Quickstart](https://cloud.google.com/run/docs/quickstarts)
- [AWS EC2 Tutorial](https://docs.aws.amazon.com/ec2/)
