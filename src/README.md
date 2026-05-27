# Source Code & ETL Pipeline (Digital Marketing Analysis)

Thư mục `src/` chứa toàn bộ mã nguồn phục vụ cho quá trình trích xuất, làm sạch, và xử lý dữ liệu (ETL - Extract, Transform, Load) cho dự án Phân tích Marketing Kỹ thuật số ngành Vật liệu xây dựng & Nội thất.

> [!NOTE]
> Pipeline hiện tại thực hiện **xử lý dữ liệu thuần túy** (rule-based / text-processing). 
> Phần phân loại cảm xúc (Sentiment Analysis) bằng mô hình học máy NLP (ví dụ: PhoBERT, XLM-R) sẽ được triển khai ở giai đoạn sau, trong notebook/module riêng biệt để phục vụ việc so sánh và lựa chọn mô hình tối ưu.

---

## 1. Cấu trúc Mã nguồn

| File | Chức năng chính |
| :--- | :--- |
| [`cleaning.py`](cleaning.py) | Chứa các hàm làm sạch dữ liệu tĩnh (Text parsing, Regex, Date formatting, tính toán tương tác, chuyển đổi kiểu dữ liệu) cho 3 nguồn: Google Reviews, Website Catalog và Facebook Posts. |
| [`nlp_processor.py`](nlp_processor.py) | Chứa các hàm tiền xử lý văn bản tiếng Việt chuẩn (Unicode NFC, lọc bỏ emoji/URL/sđt/ký tự đặc biệt) và trích xuất khía cạnh (Aspect Extraction) dựa trên bộ từ điển từ khóa chuyên ngành. **Không phụ thuộc vào mô hình học máy (ML/DL).** |
| [`pipeline.py`](pipeline.py) | Bộ điều phối chính (Orchestrator). Có nhiệm vụ liên kết `cleaning.py` và `nlp_processor.py`, đọc dữ liệu thô từ `data/raw/` và lưu trữ kết quả cuối cùng tại `data/master/`. |

---

## 2. Luồng Xử lý Dữ liệu (The Pipeline)

Quá trình ETL được chia làm 3 bước chính khi thực thi [`pipeline.py`](pipeline.py):

### Bước 1: Xử lý dữ liệu Catalog Sản phẩm
- **Nguồn thô:** `data/raw/raw_website_catalog/` (chứa tệp sản phẩm thu thập từ website).
- **Thao tác:**
  - Loại bỏ các ký tự tiền tệ ("VNĐ", "đ", dấu phẩy) trong giá bán để chuyển về dạng số thực (`float`).
  - Điền khuyết giá khuyến mãi nếu trống (Gán mặc định bằng giá gốc).
  - Tính tỷ lệ phần trăm giảm giá (`discount_rate`).
  - Tách chuỗi thư mục (category_path) thành phân cấp `category_l1` (Danh mục cấp 1) và `category_l2`.
  - Chuẩn hóa tình trạng kho hàng (`availability`) thành dạng Boolean (`True/False`).

### Bước 2: Xử lý dữ liệu Facebook Posts
- **Nguồn thô:** `data/raw/raw_facebook_posts/` (các file Excel `.xlsx`).
- **Thao tác:**
  - Làm sạch các trường text bị lỗi ký tự hiển thị.
  - Chuyển đổi toàn bộ các chỉ số tương tác (like, share, comment, wow, haha...) về dạng số nguyên (`int`).
  - **Tạo thuộc tính mới (Feature Engineering):** 
    - `total_engagement` (Tổng tương tác = Like + Share + Comment)
    - `positive_reacts` (Tổng cảm xúc tích cực = Love + Haha + Wow + Care)
    - `negative_reacts` (Tổng cảm xúc tiêu cực = Sad + Angry)

### Bước 3: Xử lý dữ liệu Google Reviews
- **Nguồn thô:** `data/raw/raw_google_reviews/` (các file CSV).
- **Thao tác:**
  - **Làm sạch chung:** Chuẩn hóa cột `rating` thành số nguyên (1 đến 5). Ước lượng ngày đánh giá tuyệt đối (`YYYY-MM-DD`) từ chuỗi thời gian tương đối (ví dụ: "3 năm trước") dựa vào mốc thời gian crawl dữ liệu.
  - **Tiền xử lý văn bản:** Chuẩn hóa Unicode NFC tiếng Việt, loại bỏ URL, email, số điện thoại, emoji và ký tự đặc biệt bằng regex, chuyển văn bản về dạng chữ thường.
  - **Trích xuất khía cạnh (Aspect Extraction):** Gắn cờ (`True/False`) nếu đánh giá nhắc đến 5 nhóm khía cạnh chính dựa trên từ điển từ khóa: `Dịch vụ` (`aspect_service`), `Giá cả` (`aspect_price`), `Sản phẩm` (`aspect_product`), `Showroom` (`aspect_showroom`), `Giao hàng/Bảo hành` (`aspect_delivery`).

---

## 3. Dữ liệu Đầu ra (Master Data)

Sau khi chạy thành công, pipeline sẽ sinh ra 3 file dữ liệu hoàn chỉnh tại thư mục `data/master/`:

1. **`master_catalog_products.csv`** (~5.000+ dòng)
   - Chứa thông tin chuẩn hóa về giá cả, tỷ lệ giảm giá, và phân cấp danh mục ngành hàng của Hoa Sen Home, Rita Võ, Viglacera.
   
2. **`master_facebook_posts.csv`** (~2.600+ dòng)
   - Chứa các chỉ số về nội dung, thời gian đăng, và chi tiết lượng tương tác của từng bài viết trên Fanpage.
   
3. **`master_google_reviews.csv`** (~1.800+ dòng)
   - Chứa review chữ gốc (`review_text`), review đã được tiền xử lý làm sạch (`cleaned_review_text`), số sao (`rating`), và nhãn khía cạnh (aspect flags).
   - **Chưa có** cột sentiment (sẽ bổ sung khi chạy mô hình NLP phân loại cảm xúc ở giai đoạn sau).

### Lưu ý về chất lượng dữ liệu Google Reviews:
* **Chênh lệch giá trị Null:** Số lượng null của `review_text` (672) và `cleaned_review_text` (675) lệch nhau 3 dòng. 
* **Nguyên nhân:** Do có 3 đánh giá gốc chỉ chứa hoàn toàn emoji hoặc ký hiệu đặc biệt (`😁 …`, `⭐️⭐️⭐️⭐️⭐️`, `💯💯💯 …`). Khi qua bộ lọc làm sạch [clean_text_for_nlp](nlp_processor.py#L39-L76), toàn bộ ký tự này bị xóa khiến văn bản trở thành chuỗi rỗng `""`, dẫn đến việc Pandas đọc lên là `NaN`.
* Chi tiết kiểm tra chất lượng dữ liệu được tích hợp tại cuối notebook [`01_data_cleaning_and_enrichment.ipynb`](../notebooks/01_data_cleaning_and_enrichment.ipynb).

---

## 4. Hướng dẫn chạy Pipeline

Đảm bảo bạn đang đứng ở thư mục gốc của dự án (`digital_marketing_analysis`).

**Cài đặt các thư viện bổ trợ:**
```bash
pip install openpyxl pandas matplotlib seaborn
```

> [!TIP]
> Do pipeline chỉ xử lý dữ liệu thuần túy nên không cần cài đặt các thư viện nặng như `torch` hay `transformers`. Chỉ cần các thư viện phân tích cơ bản và `openpyxl` để đọc tệp Excel của Facebook.

**Kích hoạt Pipeline:**
Chạy lệnh sau trên terminal:
```bash
py src/pipeline.py
```
*(Nếu hệ điều hành của bạn sử dụng lệnh `python` chuẩn thay vì `py`, hãy đổi thành: `python src/pipeline.py`)*

---

## 5. Các bước tiếp theo

1. Sử dụng notebook [`01_data_cleaning_and_enrichment.ipynb`](../notebooks/01_data_cleaning_and_enrichment.ipynb) để trực quan hóa, chạy pipeline trực tiếp và rà soát chất lượng dữ liệu.
2. Xây dựng notebook so sánh hiệu quả các mô hình ngôn ngữ tiếng Việt (PhoBERT, XLM-R, BERT...) cho bài toán phân loại cảm xúc (Sentiment Analysis).
3. Đóng gói kết quả phân tích cảm xúc để bổ sung cột `sentiment_label` và `sentiment_score` vào `master_google_reviews.csv`.
