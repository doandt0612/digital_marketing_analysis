"""
pipeline.py - File thực thi luồng dữ liệu (ETL pipeline) cho dự án Digital Marketing Analysis.

File này có nhiệm vụ:
1. Đọc dữ liệu thô (raw data) từ thư mục data/raw/.
2. Gọi các hàm làm sạch từ src/cleaning.py.
3. Gọi hàm xử lý văn bản thuần túy từ src/nlp_processor.py cho Google Reviews
   (tiền xử lý text + trích xuất khía cạnh bằng từ điển từ khóa).
4. Lưu master data vào thư mục data/master/.

Lưu ý:
    Phần phân loại cảm xúc (Sentiment Analysis) bằng mô hình NLP (PhoBERT, v.v.)
    sẽ được triển khai ở giai đoạn sau, trong notebook riêng để so sánh và lựa chọn
    mô hình phù hợp nhất.

Cấu trúc thư mục dự kiến:
- data/
  - raw/
    - raw_google_reviews/
    - raw_website_catalog/
    - raw_facebook_posts/
  - master/
    - master_google_reviews.csv
    - master_catalog_products.csv
    - master_facebook_posts.csv
"""

import os
import time

# Import các module tự viết
from cleaning import clean_google_reviews, clean_catalog_products, clean_facebook_posts
from nlp_processor import enrich_reviews_text_processing


def get_project_root():
    """Lấy đường dẫn gốc của dự án dựa trên vị trí của file này."""
    # src/pipeline.py -> dự án gốc là thư mục cha của src/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_pipeline():
    """
    Chạy toàn bộ quá trình ETL (chỉ xử lý dữ liệu thuần túy, không dùng mô hình ML).
    """
    start_time = time.time()
    
    project_root = get_project_root()
    print(f"[*] Thư mục gốc dự án: {project_root}")
    
    # Định nghĩa các đường dẫn
    raw_dir = os.path.join(project_root, "data", "raw")
    master_dir = os.path.join(project_root, "data", "master")
    
    review_dir = os.path.join(raw_dir, "raw_google_reviews")
    catalog_dir = os.path.join(raw_dir, "raw_website_catalog")
    fb_dir = os.path.join(raw_dir, "raw_facebook_posts")
    
    # Tạo thư mục master nếu chưa có
    os.makedirs(master_dir, exist_ok=True)
    
    # Đường dẫn file đầu ra
    out_reviews_path = os.path.join(master_dir, "master_google_reviews.csv")
    out_catalog_path = os.path.join(master_dir, "master_catalog_products.csv")
    out_fb_path = os.path.join(master_dir, "master_facebook_posts.csv")

    print("\n" + "="*60)
    print("BƯỚC 1: XỬ LÝ DỮ LIỆU CATALOG SẢN PHẨM")
    print("="*60)
    if os.path.exists(catalog_dir):
        print(f"[+] Đang làm sạch dữ liệu catalog từ: {catalog_dir}")
        cleaned_catalog = clean_catalog_products(catalog_dir, output_path=out_catalog_path)
        print(f"[+] Đã xử lý và lưu {len(cleaned_catalog)} sản phẩm vào: {out_catalog_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {catalog_dir}. Bỏ qua.")

    print("\n" + "="*60)
    print("BƯỚC 2: XỬ LÝ DỮ LIỆU BÀI VIẾT FACEBOOK")
    print("="*60)
    if os.path.exists(fb_dir):
        print(f"[+] Đang làm sạch dữ liệu Facebook từ: {fb_dir}")
        cleaned_fb = clean_facebook_posts(fb_dir, output_path=out_fb_path)
        print(f"[+] Đã xử lý và lưu {len(cleaned_fb)} bài viết vào: {out_fb_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {fb_dir}. Bỏ qua.")

    print("\n" + "="*60)
    print("BƯỚC 3: XỬ LÝ DỮ LIỆU GOOGLE REVIEWS (Làm sạch + Trích xuất khía cạnh)")
    print("="*60)
    if os.path.exists(review_dir):
        print(f"[+] Đang làm sạch dữ liệu Google Reviews từ: {review_dir}")
        cleaned_reviews = clean_google_reviews(review_dir, output_path=None)
        print(f"[+] Đã làm sạch {len(cleaned_reviews)} đánh giá.")
        
        if cleaned_reviews:
            print("[+] Đang xử lý văn bản (tiền xử lý + trích xuất khía cạnh từ khóa)...")
            enriched_reviews = enrich_reviews_text_processing(
                cleaned_reviews, 
                output_path=out_reviews_path
            )
            print(f"[+] Đã xử lý và lưu {len(enriched_reviews)} đánh giá vào: {out_reviews_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {review_dir}. Bỏ qua.")

    elapsed = time.time() - start_time
    print(f"HOÀN TẤT PIPELINE SAU {elapsed:.2f} GIÂY!")



if __name__ == "__main__":
    run_pipeline()
