"""
nlp_processor.py - Module tiền xử lý văn bản tiếng Việt cho dự án Digital Marketing Analysis.

Module này chỉ chứa các hàm xử lý dữ liệu văn bản THUẦN TÚY (rule-based),
KHÔNG sử dụng bất kỳ mô hình học máy (ML/DL) nào.

Các chức năng chính:
    - Chuẩn hóa Unicode NFC cho tiếng Việt.
    - Làm sạch văn bản (loại bỏ URL, emoji, ký tự đặc biệt).
    - Trích xuất khía cạnh (Aspect Extraction) dựa trên từ điển từ khóa chuyên ngành.

Lưu ý:
    Phần phân loại cảm xúc (Sentiment Analysis) bằng mô hình NLP (ví dụ PhoBERT)
    sẽ được triển khai ở giai đoạn sau, trong một notebook hoặc module riêng biệt
    để so sánh và lựa chọn mô hình phù hợp nhất.
"""

import re
import os
import csv
import unicodedata


# ============================================================================
# PHẦN 1: TIỀN XỬ LÝ VĂN BẢN TIẾNG VIỆT
# ============================================================================

def normalize_unicode(text):
    """
    Chuẩn hóa bảng mã Unicode tiếng Việt (NFC) để tránh lỗi font
    khi hai ký tự Unicode khác nhau nhưng hiển thị giống nhau.
    Ví dụ: chữ 'ồ' có thể được biểu diễn bằng 1 ký tự (NFC) hoặc 2 ký tự (NFD).
    """
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)


# Từ điển chuẩn hóa Teencode và viết tắt tiếng Việt cơ bản
TEENCODE_MAP = {
    "ko": "không",
    "k": "không",
    "khg": "không",
    "nv": "nhân viên",
    "đc": "được",
    "dc": "được",
    "sp": "sản phẩm",
    "ch": "cửa hàng",
    "ok": "tốt",
    "oke": "tốt",
    "oks": "tốt",
    "vs": "với",
    "đt": "điện thoại",
    "dt": "điện thoại",
    "tks": "cảm ơn",
    "thanks": "cảm ơn",
    "trc": "trước",
    "đg": "đang",
    "dg": "đang",
    "cug": "cũng",
    "cg": "cũng",
    "ib": "nhắn tin",
    "inbox": "nhắn tin",
    "fb": "facebook",
    "gđ": "gia đình",
    "kh": "khách hàng",
    "cty": "công ty",
    "bik": "biết",
    "bít": "biết",
    "bit": "biết",
}



def normalize_teencode(text):
    """
    Chuẩn hóa các từ viết tắt và teencode tiếng Việt phổ biến trong văn bản.
    Sử dụng regex r'\b...\b' để đảm bảo chỉ thay thế khi khớp cả từ độc lập.
    """
    if not text:
        return ""
    for word, replacement in TEENCODE_MAP.items():
        text = re.sub(rf'\b{word}\b', replacement, text)
    return text


def clean_text_for_nlp(text):
    """
    Tiền xử lý văn bản tiếng Việt trước khi đưa vào phân tích.

    Các bước xử lý:
        1. Chuẩn hóa Unicode NFC.
        2. Chuyển về chữ thường.
        3. Loại bỏ URL, email, số điện thoại.
        4. Loại bỏ emoji và ký tự đặc biệt (giữ lại chữ cái tiếng Việt, số, dấu câu cơ bản).
        5. Loại bỏ khoảng trắng thừa.
        6. Chuẩn hóa các từ viết tắt và teencode cơ bản.
    """
    if not text or not isinstance(text, str):
        return ""

    text = normalize_unicode(text)
    text = text.lower()

    # Loại bỏ URL
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    # Loại bỏ email
    text = re.sub(r'\S+@\S+\.\S+', ' ', text)

    # Loại bỏ số điện thoại (dạng 0xxx hoặc +84xxx)
    text = re.sub(r'(\+84|0)\d{8,10}', ' ', text)

    # Loại bỏ emoji và các ký tự Unicode đặc biệt (giữ lại tiếng Việt + ASCII cơ bản)
    # Dải ký tự tiếng Việt nằm trong Latin Extended + combining marks
    text = re.sub(
        r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:\-\']',
        ' ',
        text
    )

    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()

    # Chuẩn hóa teencode viết tắt
    text = normalize_teencode(text)

    return text



# ============================================================================
# PHẦN 2: PHÂN TÍCH KHÍA CẠNH (Aspect Extraction - Rule-based)
# ============================================================================

# Từ điển từ khóa chuyên ngành bán lẻ VLXD & Nội thất
ASPECT_KEYWORDS = {
    "aspect_service": {
        "keywords": [
            "nhân viên", "tư vấn", "phục vụ", "nhiệt tình", "thân thiện",
            "dễ thương", "chuyên nghiệp", "hỗ trợ", "chăm sóc", "chu đáo",
            "tiếp đón", "lịch sự", "mất lịch sự", "thái độ", "sale",
            "tận tâm", "tận tình", "vui vẻ", "niềm nở", "không nghe máy",
            "bán hàng", "nv", "nhân viên bán hàng",
        ],
        "description": "Thái độ phục vụ / Dịch vụ tư vấn nhân viên",
    },
    "aspect_price": {
        "keywords": [
            "giá", "giá cả", "đắt", "rẻ", "mắc", "chát", "hợp lý",
            "phải chăng", "tiết kiệm", "khuyến mãi", "giảm giá", "ưu đãi",
            "đúng giá", "minh bạch", "chi phí", "đáng tiền", "đáng đồng tiền",
            "giá tốt", "giá cao", "giá ok", "tốn kém",
        ],
        "description": "Giá cả / Chính sách giá",
    },
    "aspect_product": {
        "keywords": [
            "sản phẩm", "chất lượng", "hàng", "hàng hóa", "bền", "đẹp",
            "xấu", "lỗi", "trầy", "trầy xước", "hỏng", "chính hãng",
            "hàng giả", "uy tín", "mẫu mã", "đa dạng", "đúng chủng loại",
            "thiết bị", "vật liệu", "nội thất", "gạch", "tôn", "sắt",
            "bồn cầu", "lavabo", "vòi sen", "bếp", "sơn",
            "mẫu mới", "cao cấp", "sang trọng",
        ],
        "description": "Chất lượng sản phẩm / Mẫu mã hàng hóa",
    },
    "aspect_showroom": {
        "keywords": [
            "showroom", "cửa hàng", "không gian", "trưng bày", "rộng",
            "đẹp", "sạch sẽ", "thoáng", "hoành tráng", "đẳng cấp",
            "bố trí", "vị trí", "dễ tìm", "bất tiện", "chật",
            "gọn gàng", "ngăn nắp", "rộng rãi",
        ],
        "description": "Không gian / Thiết kế Showroom / Cửa hàng",
    },
    "aspect_delivery": {
        "keywords": [
            "giao hàng", "vận chuyển", "ship", "giao", "nhận hàng",
            "đóng gói", "nhanh", "chậm", "đúng hẹn", "trễ",
            "vỡ", "móp", "trầy móp", "bảo hành", "đổi trả",
            "lắp đặt", "thi công",
        ],
        "description": "Giao hàng / Vận chuyển / Bảo hành / Lắp đặt",
    },
}


def extract_aspects(text):
    """
    Trích xuất các khía cạnh (aspects) từ nội dung văn bản dựa trên từ điển từ khóa.

    Args:
        text: Chuỗi văn bản tiếng Việt (nên là text đã qua clean_text_for_nlp).

    Returns:
        dict: Từ điển với key là tên aspect và value là True/False.
              Ví dụ: {"aspect_service": True, "aspect_price": False, ...}
    """
    result = {}
    if not text or not isinstance(text, str):
        for aspect_name in ASPECT_KEYWORDS:
            result[aspect_name] = False
        return result

    text_lower = text.lower()

    for aspect_name, aspect_config in ASPECT_KEYWORDS.items():
        keywords = aspect_config["keywords"]
        found = any(kw in text_lower for kw in keywords)
        result[aspect_name] = found

    return result


# ============================================================================
# PHẦN 3: HÀM TỔNG HỢP - LÀM GIÀU REVIEWS BẰNG XỬ LÝ VĂN BẢN THUẦN TÚY
# ============================================================================

def enrich_reviews_text_processing(reviews, output_path=None):
    """
    Làm giàu danh sách reviews bằng các bước xử lý văn bản thuần túy (không dùng mô hình ML).

    Hàm này nhận đầu vào là danh sách các dict review (output từ cleaning.clean_google_reviews),
    thực hiện:
        - Tiền xử lý (clean) văn bản tiếng Việt.
        - Trích xuất khía cạnh (aspect) dựa trên từ điển từ khóa.

    Lưu ý:
        Cột sentiment_label, sentiment_score KHÔNG được gán ở bước này.
        Việc phân loại cảm xúc sẽ được thực hiện riêng ở giai đoạn chọn mô hình NLP.

    Args:
        reviews: Danh sách dict, mỗi dict chứa ít nhất trường 'review_text'.
        output_path: Đường dẫn file CSV đầu ra (tùy chọn). Nếu cung cấp, sẽ ghi kết quả ra file.

    Returns:
        list[dict]: Danh sách reviews đã được bổ sung các trường:
            - cleaned_review_text: Văn bản đã tiền xử lý.
            - aspect_service: True/False - Đề cập đến dịch vụ nhân viên.
            - aspect_price: True/False - Đề cập đến giá cả.
            - aspect_product: True/False - Đề cập đến chất lượng sản phẩm.
            - aspect_showroom: True/False - Đề cập đến không gian showroom.
            - aspect_delivery: True/False - Đề cập đến giao hàng/bảo hành.
    """
    if not reviews:
        print("[TextProcessing] Không có review nào để xử lý.")
        return reviews

    print(f"[TextProcessing] Bắt đầu xử lý văn bản cho {len(reviews)} reviews...")

    enriched_reviews = []

    for i, review in enumerate(reviews):
        enriched = dict(review)  # Sao chép toàn bộ trường gốc

        # Bước 1: Tiền xử lý văn bản
        raw_text = review.get("review_text", "")
        cleaned = clean_text_for_nlp(raw_text)
        enriched["cleaned_review_text"] = cleaned

        # Bước 2: Trích xuất khía cạnh từ khóa
        aspects = extract_aspects(cleaned)
        for aspect_name in ASPECT_KEYWORDS:
            enriched[aspect_name] = aspects.get(aspect_name, False)

        enriched_reviews.append(enriched)

    # Thống kê nhanh về aspect
    print(f"[TextProcessing] Hoàn tất xử lý văn bản cho {len(enriched_reviews)} reviews.")
    for aspect_name, aspect_config in ASPECT_KEYWORDS.items():
        count = sum(1 for r in enriched_reviews if r.get(aspect_name, False))
        print(f"  - {aspect_config['description']}: {count} reviews đề cập")

    # Thống kê review có nội dung vs không có nội dung
    has_text = sum(1 for r in enriched_reviews if r.get("cleaned_review_text", ""))
    no_text = len(enriched_reviews) - has_text
    print(f"  - Reviews có nội dung chữ: {has_text}")
    print(f"  - Reviews chỉ có số sao (không có chữ): {no_text}")

    # Ghi ra file CSV nếu cần
    if output_path and enriched_reviews:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        headers = list(enriched_reviews[0].keys())
        with open(output_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(enriched_reviews)
        print(f"[TextProcessing] Đã lưu kết quả tại: {output_path}")

    return enriched_reviews
