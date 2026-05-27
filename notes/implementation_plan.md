# Kế hoạch xử lý dữ liệu thô (Digital Marketing Analysis Pipeline)

Tài liệu này đề xuất phương án và kế hoạch chi tiết để làm sạch, gộp dữ liệu và phân tích chuyên sâu cho ba nguồn dữ liệu chính trong dự án: Google Maps Reviews, Website Product Catalog, và Facebook Posts của các thương hiệu **Hoa Sen Home**, **Rita Võ**, và **Viglacera (cùng Vietceramics ở mảng catalog)**.

---

## Phân tích hiện trạng dữ liệu thô (Raw Data)

Dựa trên việc đọc và phân tích cấu trúc thực tế của các file trong `data/raw/`:

1. **Google Maps Reviews (`data/raw/raw_google_review/`)**:
   * Gồm 3 file: `Hoa Sen Home` (440 dòng), `Rita Vo` (998 dòng), `Viglacera` (392 dòng).
   * **Đặc điểm**: File Hoa Sen Home có thêm cột `stage2_finished_at` (thời điểm crawl là khoảng `2026-05-22`), 2 file còn lại chỉ có mốc thời gian tương đối (`review_date`). Cột `rating` chứa dạng text (`5 sao`).
2. **Website Product Catalog (`data/raw/raw_website_catalog/`)**:
   * Gồm các file riêng lẻ của từng thương hiệu (`hoa_sen_home_products.csv` - 2340 dòng, `rita_vo_products.csv` - 2402 dòng, `viglacera_products.csv` - 321 dòng) và tệp tổng hợp `balanced_products.csv` (5063 dòng - đúng bằng tổng của 3 file trên).
   * **Đặc điểm**: File có cấu trúc rất chi tiết (32 cột), chứa thông tin về giá bán (`regular_price_vnd`, `sale_price_vnd`), đường dẫn danh mục (`category_path`), và mô tả sản phẩm (`description`).
3. **Facebook Posts (`data/raw/raw_facebook_post/`)**:
   * Gồm 3 file Excel `.xlsx` cho Hoa Sen Home, Rita Võ, và Viglacera.
   * **Đặc điểm**: Chứa thông tin về bài viết, thời gian đăng bài và các chỉ số tương tác rất chi tiết như lượt thích (`likes`), bình luận (`comments`), chia sẻ (`shares`), lượt xem video (`viewsCount`) và các loại cảm xúc chi tiết (`reactionLoveCount`, `reactionAngryCount`, v.v.).

---

## Định hướng Xử lý Dữ liệu (ETL & NLP Enrichment Pipeline)

Chúng ta sẽ áp dụng **Cách 2** (Tích hợp trực tiếp các phân tích chuyên sâu vào Data Master để tối ưu hóa việc trực quan hóa sau này). Quy trình xử lý sẽ tạo ra 3 bảng dữ liệu Master chính:

### 1. Dữ liệu Master Google Reviews (`master_google_reviews.csv`)
* **Gộp dữ liệu**: Gộp 3 file review thành 1 bảng duy nhất, gán nhãn `brand`.
* **Ước lượng Ngày đánh giá**: Chuyển đổi cột `review_date` tương đối (ví dụ: `9 tháng trước`) thành ngày tháng cụ thể (`YYYY-MM-DD`) dựa trên mốc thời gian crawl dữ liệu (khoảng `2026-05-22`).
* **Làm sạch nội dung**: Chuẩn hóa text tiếng Việt, loại bỏ ký tự đặc biệt, chuẩn hóa rating thành số (`1` đến `5`).
* **Làm giàu NLP**:
  * Chạy mô hình phân tích cảm xúc tiếng Việt để gán nhãn `sentiment` (`Positive`, `Negative`, `Neutral`) và điểm số `sentiment_score`.
  * Trích xuất các khía cạnh dịch vụ (`aspect_price`, `aspect_service`, `aspect_product`, `aspect_showroom`, `aspect_delivery`) để phục vụ việc lọc và trực quan hóa chi tiết.

### 2. Dữ liệu Master Catalog Sản phẩm (`master_products.csv`)
* **Nguồn dữ liệu**: Sử dụng file gộp sẵn `balanced_products.csv` làm gốc.
* **Làm sạch giá bán**: Chuẩn hóa `regular_price_vnd` và `sale_price_vnd` sang dạng số. Tính toán tỷ lệ giảm giá (`discount_rate`). Gán nhãn các sản phẩm "Liên hệ báo giá" khi giá bằng 0 hoặc null.
* **Phân tách danh mục**: Tách chuỗi `category_path` (được phân cách bởi dấu gạch đứng `|` hoặc dấu mũi tên `>`) thành các trường danh mục cấp 1 (`category_l1`), cấp 2 (`category_l2`) để so sánh ngành hàng giữa các thương hiệu.
* **Phân loại trạng thái kho**: Chuẩn hóa cột `availability` về dạng Boolean (`True`/`False`).

### 3. Dữ liệu Master Facebook Posts (`master_facebook_posts.csv`)
* **Gộp dữ liệu**: Gộp 3 file Excel thành 1 bảng, gán nhãn `brand` từ tên trang.
* **Làm sạch thời gian**: Định dạng cột `time` thành kiểu datetime chuẩn để phân tích xu hướng bài đăng theo giờ/thứ trong tuần.
* **Phân tích Tương tác (Engagement Metrics)**:
  * Tính tổng lượng tương tác: `total_engagement = likes + comments + shares`.
  * Tính điểm phản ứng cảm xúc: Tỷ lệ cảm xúc tích cực (`reactionLoveCount`, `reactionHahaCount`, `reactionWowCount`) so với tiêu cực (`reactionAngryCount`, `reactionSadCount`) để xác định bài viết nào thu hút phản ứng tốt hoặc gây tranh cãi.
  * Phân loại bài viết có video (`isVideo = True`/`False`) để phân tích định dạng content nào hiệu quả hơn.

---

## Đề xuất Thay đổi trong Codebase

Để triển khai pipeline này, cấu trúc thư mục mới sẽ như sau:

* **[NEW]** [cleaning.py](file:///d:/PROJECT/digital_marketing_analysis/src/cleaning.py): Chứa các hàm xử lý logic làm sạch, chuyển đổi kiểu dữ liệu, ước lượng ngày review và tính toán chỉ số tương tác Facebook.
* **[NEW]** [nlp_processor.py](file:///d:/PROJECT/digital_marketing_analysis/src/nlp_processor.py): Chứa module phân tích cảm xúc (Sentiment) và phân loại khía cạnh (Aspect) dựa trên từ khóa tiếng Việt hoặc mô hình học máy.
* **[NEW]** [pipeline.py](file:///d:/PROJECT/digital_marketing_analysis/src/pipeline.py): Tập lệnh chạy toàn bộ quy trình ETL để biến đổi dữ liệu từ `data/raw/` thành các tệp sạch trong `data/master/`.
* **[NEW]** [01_data_cleaning_and_enrichment.ipynb](file:///d:/PROJECT/digital_marketing_analysis/notebooks/01_data_cleaning_and_enrichment.ipynb): Notebook mẫu chạy pipeline trực quan và kiểm tra chất lượng dữ liệu đầu ra.
* **[NEW]** [02_marketing_insights_dashboard.ipynb](file:///d:/PROJECT/digital_marketing_analysis/notebooks/02_marketing_insights_dashboard.ipynb): Notebook phân tích EDA và vẽ biểu đồ so sánh sức khỏe thương hiệu, định vị giá sản phẩm và hiệu quả fanpage Facebook.

---

## Kế hoạch Xác minh (Verification Plan)

### Kiểm tra tự động bằng Python:
* Kiểm tra số lượng dòng của dữ liệu master sau khi gộp (ví dụ: `master_reviews` phải có đúng 440 + 998 + 392 = 1830 dòng).
* Kiểm tra các giá trị khuyết thiếu (`null`) trên các trường khóa chính như `brand`, `rating`, `regular_price_vnd`, `likes`.
* Xác thực định dạng ngày tháng có thể phân tích được trên chuỗi thời gian (`pd.to_datetime`).

### Kiểm tra thủ công:
* Mở các file master trong Excel hoặc pandas để xác nhận dữ liệu đã được gán nhãn `sentiment` chính xác (ví dụ: các câu có từ "tệ", "mất lịch sự" phải được gán nhãn `Negative`).
* Vẽ thử biểu đồ phân phối giá sản phẩm và lượng tương tác Facebook để đảm bảo không có dữ liệu nhiễu (outliers).
