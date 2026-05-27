"""
pipeline.py - File thực thi luồng dữ liệu (ETL pipeline) cho dự án Digital Marketing Analysis.

File này có nhiệm vụ:
1. Đọc dữ liệu thô (raw data) từ thư mục data/raw/.
2. Gọi các hàm làm sạch từ src/cleaning.py.
3. Gọi hàm phân tích NLP từ src/nlp_processor.py cho dữ liệu reviews.
4. Lưu master data vào thư mục data/master/.

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
import argparse

# Import các module tự viết
from cleaning import clean_google_reviews, clean_catalog_products, clean_facebook_posts
from nlp_processor import enrich_reviews_with_nlp


def get_project_root():
    """Lấy đường dẫn gốc của dự án dựa trên vị trí của file này."""
    # src/pipeline.py -> dự án gốc là thư mục cha của src/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_pipeline(batch_size=16):
    """
    Chạy toàn bộ quá trình ETL.
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

    print("\n" + "="*50)
    print("BƯỚC 1: XỬ LÝ DỮ LIỆU CATALOG SẢN PHẨM")
    print("="*50)
    if os.path.exists(catalog_dir):
        print(f"[+] Đang làm sạch dữ liệu catalog từ: {catalog_dir}")
        cleaned_catalog = clean_catalog_products(catalog_dir, output_path=out_catalog_path)
        print(f"[+] Đã xử lý và lưu {len(cleaned_catalog)} sản phẩm vào: {out_catalog_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {catalog_dir}. Bỏ qua.")

    print("\n" + "="*50)
    print("BƯỚC 2: XỬ LÝ DỮ LIỆU BÀI VIẾT FACEBOOK")
    print("="*50)
    if os.path.exists(fb_dir):
        print(f"[+] Đang làm sạch dữ liệu Facebook từ: {fb_dir}")
        cleaned_fb = clean_facebook_posts(fb_dir, output_path=out_fb_path)
        print(f"[+] Đã xử lý và lưu {len(cleaned_fb)} bài viết vào: {out_fb_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {fb_dir}. Bỏ qua.")

    print("\n" + "="*50)
    print("BƯỚC 3: XỬ LÝ VÀ PHÂN TÍCH NLP DỮ LIỆU GOOGLE REVIEWS")
    print("="*50)
    if os.path.exists(review_dir):
        print(f"[+] Đang làm sạch dữ liệu Google Reviews từ: {review_dir}")
        # Không truyền output_path vì chúng ta sẽ ghi đè sau khi chạy NLP
        cleaned_reviews = clean_google_reviews(review_dir, output_path=None)
        print(f"[+] Đã làm sạch {len(cleaned_reviews)} đánh giá.")
        
        if cleaned_reviews:
            print("[+] Đang chạy phân tích NLP (Sentiment & Aspect)...")
            enriched_reviews = enrich_reviews_with_nlp(
                cleaned_reviews, 
                output_path=out_reviews_path, 
                batch_size=batch_size
            )
            print(f"[+] Đã xử lý NLP và lưu {len(enriched_reviews)} đánh giá vào: {out_reviews_path}")
    else:
        print(f"[-] Không tìm thấy thư mục {review_dir}. Bỏ qua.")

    elapsed = time.time() - start_time
    print("\n" + "="*50)
    print(f"HOÀN TẤT PIPELINE SAU {elapsed:.2f} GIÂY!")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy pipeline tổng hợp dữ liệu (ETL & NLP)")
    parser.add_argument(
        "--batch_size", 
        type=int, 
        default=16, 
        help="Kích thước batch khi chạy mô hình PhoBERT NLP (mặc định: 16)"
    )
    
    args = parser.parse_args()
    
    run_pipeline(batch_size=args.batch_size)
