# Hướng dẫn cài đặt Odoo trên Linux

## Yêu cầu hệ thống

Trước khi bắt đầu, hãy đảm bảo rằng bạn đã cài đặt các thành phần sau:

- **Git**
- **Docker**
- **PostgreSQL** (bỏ qua nếu bạn chạy PostgreSQL bằng Docker image)
- **Python 3.10** trở lên

---

## Các bước cài đặt

### 1. Cài đặt các gói phụ thuộc

Chạy script sau để cài đặt các gói cần thiết:

```bash
sudo ./setup/debinstall.sh
```

---

### 2. Tạo cơ sở dữ liệu và người dùng PostgreSQL cho Odoo

Đăng nhập vào PostgreSQL và tạo user, database cho Odoo:

```sql
CREATE USER admin WITH PASSWORD 'admin';
CREATE DATABASE inventory OWNER admin;
```

---

### 3. Cấu hình môi trường

Tạo file cấu hình `.odoorc` trong thư mục gốc dự án:

```ini
[options]
db_host = localhost
db_port = 5432
db_user = admin
db_password = admin
db_name = inventory
addons_path = /home/hoanh/work/odoo/addons,/home/hoanh/work/odoo/odoo/addons
```

> 💡 Lưu ý: Thay đổi đường dẫn `addons_path` cho phù hợp với môi trường của bạn.

---

### 4. Khởi chạy Odoo

Chạy lệnh sau để khởi động Odoo với file cấu hình vừa tạo:

```bash
python3 odoo-bin --config .odoorc
```

---

✅ Odoo của bạn đã sẵn sàng chạy trên Linux!
