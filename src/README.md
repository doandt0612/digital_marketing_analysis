# Source Code & ETL Pipeline (Digital Marketing Analysis)

Thư mục `src/` chứa toàn bộ mã nguồn phục vụ cho quá trình trích xuất, làm sạch, và làm giàu dữ liệu (ETL - Extract, Transform, Load) kết hợp với Trí tuệ Nhân tạo (NLP) cho dự án Phân tích Marketing Kỹ thuật số ngành Vật liệu xây dựng & Nội thất.

---

## 1. Cấu trúc Mã nguồn

| File | Chức năng chính |
| :--- | :--- |
| `cleaning.py` | Chứa các hàm làm sạch dữ liệu tĩnh (Text parsing, Regex, Date formatting, tính toán tương tác, chuyển đổi kiểu dữ liệu) cho 3 nguồn dữ liệu: Google, Catalog và Facebook. |
| `nlp_processor.py` | Chứa class và hàm xử lý Xử lý Ngôn ngữ Tự nhiên (NLP). Tích hợp mô hình AI **PhoBERT** (`wonrax/phobert-base-vietnamese-sentiment`) để dán nhãn cảm xúc và trích xuất từ khóa khía cạnh (Aspect-Based) cho Google Reviews. |
| `pipeline.py` | File thực thi chính (Orchestrator). Có nhiệm vụ móc nối `cleaning.py` và `nlp_processor.py`, đọc dữ liệu thô từ `data/raw/` và xuất kết quả cuối cùng ra thư mục `data/master/`. |

---

## 2. Luồng Xử lý Dữ liệu (The Pipeline)

Quá trình ETL được chia làm 3 bước chính khi bạn chạy file `pipeline.py`:

### Bước 1: Xử lý dữ liệu Catalog Sản phẩm
- **Nguồn thô:** `data/raw/raw_website_catalog/` (các file CSV chứa thông tin sản phẩm thu thập từ website).
- **Thao tác:** 
  - Loại bỏ các ký tự tiền tệ ("VNĐ", "đ", dấu phẩy) trong giá bán để chuyển về dạng số thực (`float`).
  - Điền khuyết giá khuyến mãi nếu trống (Gán bằng giá gốc).
  - Tách chuỗi thư mục (category_path) thành `category_l1` (Danh mục cấp 1) và `category_l2`.
  - Chuẩn hóa tình trạng kho hàng (`availability`) thành dạng Boolean (`True/False`).

### Bước 2: Xử lý dữ liệu Facebook Posts
- **Nguồn thô:** `data/raw/raw_facebook_posts/` (các file Excel `.xlsx`).
- **Thao tác:**
  - Làm sạch các trường text bị lỗi ký tự.
  - Chuyển đổi toàn bộ các chỉ số tương tác (like, share, comment, wow, haha...) về dạng số nguyên (`int64`).
  - **Tạo Feature mới:** Tính toán cột `total_engagement` (Tổng tương tác = Like + Share + Comment).

### Bước 3: Làm sạch và Phân tích NLP Google Reviews
- **Nguồn thô:** `data/raw/raw_google_reviews/` (các file CSV).
- **Thao tác:**
  - **Làm sạch:** Dịch ngày tháng tương đối ("3 năm trước", "2 tháng trước") ra định dạng ngày chuẩn (`YYYY-MM-DD`). Chuẩn hóa cột `rating` thành số nguyên 1-5.
  - **NLP - Phân tích cảm xúc (Sentiment Analysis):** Chạy nội dung chữ qua mô hình học sâu **PhoBERT**. Hệ thống sẽ tự động gán nhãn `Positive`, `Negative`, hoặc `Neutral`.
  - **Luật suy luận (Inference Rule):** Với những review chỉ có để lại số sao mà không viết chữ: `4-5 sao -> Positive`, `3 sao -> Neutral`, `1-2 sao -> Negative`.
  - **NLP - Phân tích khía cạnh (Aspect Extraction):** Gắn cờ (`True/False`) nếu khách hàng nhắc đến 5 nhóm khía cạnh trọng tâm: `Dịch vụ`, `Giá cả`, `Sản phẩm`, `Showroom`, `Giao hàng`.

---

## 3. Dữ liệu Đầu ra (Master Data)

Sau khi chạy thành công, pipeline sẽ sinh ra 3 file dữ liệu hoàn chỉnh tại thư mục `data/master/` để phục vụ trực tiếp cho quá trình vẽ Biểu đồ & Dashboard:

1. **`master_catalog_products.csv`** (~5.000+ sản phẩm)
   - Chứa thông tin chuẩn hóa về giá cả, tỷ lệ giảm giá (`discount_rate`), và danh mục ngành hàng của Hoa Sen Home, Rita Võ, Viglacera.
   - Sẵn sàng để phân tích: *Chiến lược giá (Pricing Strategy), Mức độ đa dạng danh mục.*

2. **`master_facebook_posts.csv`** (~2.600+ bài viết)
   - Chứa các chỉ số về nội dung, thời gian đăng, và chi tiết từng loại cảm xúc (react_love, react_haha...).
   - Sẵn sàng để phân tích: *Khung giờ vàng đăng bài, Mức độ lan tỏa (Viral), Thị phần tương tác (Voice of Market).*

3. **`master_google_reviews.csv`** (~1.800+ đánh giá)
   - Chứa review chữ, số sao, và các nhãn NLP.
   - Sẵn sàng để phân tích: *Chỉ số hài lòng khách hàng (Sentiment Trend), Điểm nghẽn dịch vụ (Dựa trên Aspect Extraction).*

---

## 4. Hướng dẫn chạy Pipeline

Đảm bảo bạn đang đứng ở thư mục gốc của dự án (`d:\PROJECT\digital_marketing_analysis`).

**Cài đặt thư viện yêu cầu (NLP):**
```bash
pip install torch transformers pandas openpyxl
```

**Kích hoạt Pipeline:**
Chạy lệnh sau trên terminal:
```bash
python src/pipeline.py
```
*(Nếu sử dụng Windows mà lệnh `python` không hoạt động, hãy thay bằng `py src/pipeline.py`)*

**Tùy chỉnh cấu hình phần cứng (Cho máy yếu/mạnh):**
Tham số `--batch_size` cho phép điều chỉnh lượng câu review đưa vào RAM cùng lúc (Mặc định là 16).
```bash
python src/pipeline.py --batch_size 32
```
