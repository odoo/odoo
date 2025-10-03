# Giải pháp đơn giản cho lỗi Wkhtmltopdf trong Odoo 19

## Vấn đề
Lỗi `Wkhtmltopdf failed (error code: -11). Memory limit too low or maximum file number of subprocess reached.` khi gửi email từ Sale Order.

## Giải pháp
Chỉ khắc phục lỗi Wkhtmltopdf mà **KHÔNG** thay đổi giao diện mặc định của Odoo 19.

### Các file đã tạo/sửa:

1. **`sale/models/ir_actions_report_simple.py`** - Xử lý Wkhtmltopdf với các tùy chọn được hỗ trợ
2. **`sale/data/ir_config_parameter_wkhtmltopdf.xml`** - Cấu hình tham số Wkhtmltopdf
3. **`sale/data/ir_config_parameter_email_simple.xml`** - Cấu hình email đơn giản
4. **`sale/__manifest__.py`** - Thêm data files mới

### Tính năng:
- ✅ Giữ nguyên popup mặc định của Odoo 19
- ✅ Khắc phục lỗi Wkhtmltopdf với nhiều chiến lược fallback
- ✅ Chỉ sử dụng các tùy chọn được hỗ trợ
- ✅ Xử lý chunked cho báo cáo lớn
- ✅ Retry logic với exponential backoff
- ✅ Cấu hình email đơn giản

### Cách sử dụng:
1. **Restart Odoo service** để load các thay đổi
2. **Sử dụng bình thường** - bấm "Send by Email" sẽ hiện popup như mặc định
3. **Hệ thống tự động** khắc phục lỗi Wkhtmltopdf

### Cấu hình email (nếu cần):
- Vào Settings > Technical > System Parameters
- Kiểm tra các tham số:
  - `mail.default.from`: noreply@localhost
  - `mail.catchall.domain`: localhost

### Kết quả:
- ✅ Popup gửi email giữ nguyên như mặc định
- ✅ Không còn lỗi Wkhtmltopdf
- ✅ Email được gửi thành công
