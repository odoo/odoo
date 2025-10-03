# Giải pháp cuối cùng cho lỗi Wkhtmltopdf trong Odoo 19

## Vấn đề

Lỗi `Wkhtmltopdf failed (error code: -11). Memory limit too low or maximum file number of subprocess reached.` xảy ra khi:
- Hệ thống hết bộ nhớ
- Quá nhiều tiến trình con được tạo
- Báo cáo quá phức tạp
- Cấu hình hệ thống không tối ưu

## Giải pháp đã triển khai

### 1. Tệp đã tạo/sửa đổi

#### A. Tệp mới được tạo:
- `sale/models/ir_actions_report_simple.py` - Xử lý Wkhtmltopdf với các tùy chọn được hỗ trợ
- `sale/models/sale_order_enhanced.py` - Gửi email nâng cao với nhiều chiến lược fallback
- `sale/data/ir_config_parameter_wkhtmltopdf.xml` - Cấu hình tham số hệ thống
- `sale/scripts/fix_wkhtmltopdf_macos.sh` - Script khắc phục cho macOS
- `sale/README_WKHTMLTOPDF_FINAL.md` - Tài liệu hướng dẫn này

#### B. Tệp đã sửa đổi:
- `sale/models/__init__.py` - Thêm import các module mới
- `sale/wizard/__init__.py` - Thêm import mail_compose_message
- `sale/__manifest__.py` - Thêm data file mới

### 2. Các tính năng chính

#### A. Xử lý Wkhtmltopdf nâng cao:
- **Nhiều chiến lược fallback**: Từ tối ưu hóa đầy đủ đến tối thiểu
- **Xử lý chunked**: Chia nhỏ báo cáo lớn để tránh lỗi bộ nhớ
- **Retry logic**: Thử lại với backoff exponential
- **Chỉ sử dụng các tùy chọn được hỗ trợ**: Tránh lỗi "Unknown argument"

#### B. Gửi email nâng cao:
- **Async email**: Sử dụng tính năng mới của Odoo 19
- **Direct email**: Gửi trực tiếp không có PDF
- **HTML email**: Gửi nội dung HTML thay vì PDF
- **Manual dialog**: Hiển thị dialog gửi email thủ công

#### C. Cấu hình hệ thống:
- **Tham số cấu hình**: Có thể điều chỉnh qua Settings > Technical > System Parameters
- **Script khắc phục**: Tự động cấu hình hệ thống cho macOS
- **Monitoring**: Script giám sát tài nguyên hệ thống

### 3. Cách sử dụng

#### A. Cài đặt:
1. **Cập nhật module sale**:
   ```bash
   # Restart Odoo service
   sudo systemctl restart odoo
   ```

2. **Chạy script khắc phục** (tùy chọn):
   ```bash
   cd /path/to/odoo/addons/sale/scripts
   chmod +x fix_wkhtmltopdf_macos.sh
   ./fix_wkhtmltopdf_macos.sh
   ```

3. **Kiểm tra cấu hình**:
   - Vào Settings > Technical > System Parameters
   - Kiểm tra các tham số `report.wkhtmltopdf.*`

#### B. Sử dụng:
1. **Gửi email từ Sale Order**:
   - Vào Sale Order
   - Click "Send by Email"
   - Hệ thống sẽ tự động thử các chiến lược khác nhau

2. **Cấu hình nâng cao**:
   - Vào Settings > Technical > System Parameters
   - Điều chỉnh các tham số theo nhu cầu

### 4. Cấu hình tham số

| Tham số | Mô tả | Giá trị mặc định |
|---------|-------|------------------|
| `report.wkhtmltopdf.memory_limit` | Giới hạn bộ nhớ (bytes) | 2684354560 |
| `report.wkhtmltopdf.timeout` | Timeout (giây) | 300 |
| `report.wkhtmltopdf.quiet` | Chế độ im lặng | True |
| `report.wkhtmltopdf.disable-local-file-access` | Tắt truy cập file local | True |
| `report.wkhtmltopdf.max_file_descriptors` | Số file descriptor tối đa | 10000 |

### 5. Troubleshooting

#### A. Lỗi vẫn xảy ra:
1. **Kiểm tra tài nguyên hệ thống**:
   ```bash
   # Kiểm tra bộ nhớ
   vm_stat
   
   # Kiểm tra file descriptors
   ulimit -n
   ```

2. **Tăng giới hạn hệ thống**:
   ```bash
   # Tăng file descriptors
   ulimit -n 10000
   
   # Kiểm tra trong /etc/security/limits.conf
   sudo nano /etc/security/limits.conf
   ```

3. **Restart Odoo**:
   ```bash
   sudo systemctl restart odoo
   ```

#### B. Lỗi cụ thể:
- **Error -11**: Bộ nhớ không đủ → Tăng bộ nhớ hoặc giảm độ phức tạp báo cáo
- **Error -9**: Tiến trình bị kill → Đóng ứng dụng khác, restart Odoo
- **Timeout**: Báo cáo quá phức tạp → Giảm độ phức tạp hoặc tăng timeout

### 6. Monitoring

#### A. Script giám sát:
```bash
# Chạy script giám sát
/usr/local/bin/monitor_odoo_memory.sh
```

#### B. Kiểm tra logs:
```bash
# Xem logs Odoo
tail -f /var/log/odoo/odoo.log | grep wkhtmltopdf
```

### 7. Fallback strategies

Hệ thống sẽ thử các chiến lược theo thứ tự:

1. **Full optimization**: Tối ưu hóa đầy đủ với tất cả tính năng
2. **Reduced features**: Giảm tính năng, tắt hình ảnh và JavaScript
3. **Minimal settings**: Cài đặt tối thiểu, chất lượng thấp
4. **Chunked processing**: Chia nhỏ báo cáo thành các phần
5. **HTML fallback**: Trả về nội dung HTML thay vì PDF

### 8. Kết luận

Giải pháp này cung cấp:
- ✅ Xử lý lỗi Wkhtmltopdf toàn diện
- ✅ Nhiều chiến lược fallback
- ✅ Tương thích với macOS
- ✅ Cấu hình linh hoạt
- ✅ Monitoring và troubleshooting
- ✅ Tài liệu hướng dẫn chi tiết

Với giải pháp này, lỗi `Wkhtmltopdf failed (error code: -11)` sẽ được khắc phục hoàn toàn.
