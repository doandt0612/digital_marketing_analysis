"""
nlp_processor.py - Module phân tích ngôn ngữ tự nhiên tiếng Việt cho dự án Digital Marketing Analysis.

Module này sử dụng mô hình PhoBERT (wonrax/phobert-base-vietnamese-sentiment) để phân loại
cảm xúc các đánh giá (review) của khách hàng, kết hợp với phân tích khía cạnh (Aspect-Based)
dựa trên từ điển từ khóa chuyên ngành bán lẻ vật liệu xây dựng và nội thất.

Yêu cầu cài đặt:
    pip install torch transformers

Mô hình sử dụng:
    - wonrax/phobert-base-vietnamese-sentiment: Mô hình PhoBERT đã được fine-tune
      cho bài toán phân loại cảm xúc tiếng Việt (3 lớp: Positive, Negative, Neutral).
"""

import re
import os
import csv
import unicodedata


# PHẦN 1: TIỀN XỬ LÝ VĂN BẢN TIẾNG VIỆT

def normalize_unicode(text):
    """
    Chuẩn hóa bảng mã Unicode tiếng Việt (NFC) để tránh lỗi font
    khi hai ký tự Unicode khác nhau nhưng hiển thị giống nhau.
    Ví dụ: chữ 'ồ' có thể được biểu diễn bằng 1 ký tự (NFC) hoặc 2 ký tự (NFD).
    """
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)


def clean_text_for_nlp(text):
    """
    Tiền xử lý văn bản tiếng Việt trước khi đưa vào mô hình NLP.

    Các bước xử lý:
        1. Chuẩn hóa Unicode NFC.
        2. Chuyển về chữ thường.
        3. Loại bỏ URL, email, số điện thoại.
        4. Loại bỏ emoji và ký tự đặc biệt (giữ lại chữ cái tiếng Việt, số, dấu câu cơ bản).
        5. Loại bỏ khoảng trắng thừa.
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

    return text


# PHẦN 2: PHÂN TÍCH CẢM XÚC BẰNG PHOBERT (Sentiment Analysis)

class PhoBERTSentimentAnalyzer:
    """
    Bộ phân tích cảm xúc tiếng Việt sử dụng mô hình PhoBERT đã fine-tune.

    Mô hình mặc định: wonrax/phobert-base-vietnamese-sentiment
    - Output 3 lớp: NEG (Negative), POS (Positive), NEU (Neutral)

    Attributes:
        model_name (str): Tên mô hình trên Hugging Face Hub.
        device (str): Thiết bị chạy mô hình ('cpu' hoặc 'cuda').
        batch_size (int): Số lượng câu xử lý trong mỗi batch.
        max_length (int): Độ dài tối đa của chuỗi token đầu vào (PhoBERT hỗ trợ tối đa 256).
    """

    # Ánh xạ nhãn đầu ra của mô hình sang nhãn chuẩn hóa
    LABEL_MAP = {
        "NEG": "Negative",
        "POS": "Positive",
        "NEU": "Neutral",
        # Phòng hờ các biến thể khác của nhãn
        "NEGATIVE": "Negative",
        "POSITIVE": "Positive",
        "NEUTRAL": "Neutral",
        "LABEL_0": "Negative",
        "LABEL_1": "Positive",
        "LABEL_2": "Neutral",
    }

    def __init__(
        self,
        model_name="wonrax/phobert-base-vietnamese-sentiment",
        device=None,
        batch_size=16,
        max_length=256,
    ):
        """
        Khởi tạo bộ phân tích cảm xúc.

        Args:
            model_name: Tên hoặc đường dẫn đến mô hình PhoBERT sentiment trên Hugging Face.
            device: Thiết bị chạy ('cpu', 'cuda', 'cuda:0', ...). Nếu None, tự động chọn.
            batch_size: Số lượng review xử lý đồng thời trong mỗi batch.
            max_length: Chiều dài token tối đa (PhoBERT giới hạn 256 token).
        """
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
        except ImportError:
            raise ImportError(
                "Cần cài đặt 'torch' và 'transformers' để sử dụng PhoBERT.\n"
                "Chạy lệnh: pip install torch transformers"
            )

        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length

        # Tự động chọn thiết bị (GPU nếu có)
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"[NLP] Đang tải mô hình PhoBERT từ '{model_name}'...")
        print(f"[NLP] Thiết bị sử dụng: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()  # Chuyển sang chế độ đánh giá (inference)

        # Lấy ánh xạ ID -> Nhãn từ config của mô hình
        self._id2label = self.model.config.id2label
        print(f"[NLP] Mô hình đã tải thành công. Các nhãn: {self._id2label}")

    def _normalize_label(self, raw_label):
        """Chuẩn hóa nhãn đầu ra của mô hình về dạng thống nhất."""
        raw_upper = str(raw_label).upper().strip()
        return self.LABEL_MAP.get(raw_upper, raw_label)

    def predict_single(self, text):
        """
        Dự đoán cảm xúc cho một câu văn bản duy nhất.

        Args:
            text: Chuỗi văn bản tiếng Việt cần phân tích.

        Returns:
            dict: {
                "sentiment_label": "Positive" | "Negative" | "Neutral",
                "sentiment_score": float (0.0 - 1.0),
                "all_scores": {"Positive": float, "Negative": float, "Neutral": float}
            }
        """
        import torch

        if not text or not text.strip():
            return {
                "sentiment_label": "Neutral",
                "sentiment_score": 0.0,
                "all_scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0},
            }

        cleaned = clean_text_for_nlp(text)
        if not cleaned:
            return {
                "sentiment_label": "Neutral",
                "sentiment_score": 0.0,
                "all_scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0},
            }

        inputs = self.tokenizer(
            cleaned,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        probs_list = probs[0].cpu().tolist()

        # Xây dựng bảng điểm cho từng nhãn
        all_scores = {}
        for idx, score in enumerate(probs_list):
            raw_label = self._id2label.get(idx, f"LABEL_{idx}")
            normalized = self._normalize_label(raw_label)
            all_scores[normalized] = round(score, 4)

        # Chọn nhãn có điểm cao nhất
        best_label = max(all_scores, key=all_scores.get)
        best_score = all_scores[best_label]

        return {
            "sentiment_label": best_label,
            "sentiment_score": round(best_score, 4),
            "all_scores": all_scores,
        }

    def predict_batch(self, texts):
        """
        Dự đoán cảm xúc cho một danh sách văn bản (xử lý theo batch để tối ưu tốc độ).

        Args:
            texts: Danh sách các chuỗi văn bản tiếng Việt.

        Returns:
            list[dict]: Danh sách kết quả, mỗi phần tử có cấu trúc giống predict_single.
        """
        import torch

        results = []
        cleaned_texts = []
        valid_indices = []

        # Bước 1: Tiền xử lý và đánh dấu các review hợp lệ (có nội dung)
        for i, text in enumerate(texts):
            cleaned = clean_text_for_nlp(text) if text else ""
            if cleaned:
                cleaned_texts.append(cleaned)
                valid_indices.append(i)

        # Khởi tạo kết quả mặc định cho tất cả review (kể cả review trống)
        default_result = {
            "sentiment_label": "Neutral",
            "sentiment_score": 0.0,
            "all_scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0},
        }
        results = [dict(default_result) for _ in texts]

        # Bước 2: Xử lý theo batch
        total_valid = len(cleaned_texts)
        if total_valid == 0:
            return results

        for start in range(0, total_valid, self.batch_size):
            end = min(start + self.batch_size, total_valid)
            batch_texts = cleaned_texts[start:end]
            batch_indices = valid_indices[start:end]

            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
                padding=True,
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            for j, idx in enumerate(batch_indices):
                prob_values = probs[j].cpu().tolist()

                all_scores = {}
                for label_id, score in enumerate(prob_values):
                    raw_label = self._id2label.get(label_id, f"LABEL_{label_id}")
                    normalized = self._normalize_label(raw_label)
                    all_scores[normalized] = round(score, 4)

                best_label = max(all_scores, key=all_scores.get)
                best_score = all_scores[best_label]

                results[idx] = {
                    "sentiment_label": best_label,
                    "sentiment_score": round(best_score, 4),
                    "all_scores": all_scores,
                }

            # Hiển thị tiến độ
            processed = min(end, total_valid)
            print(f"[NLP] Đã xử lý sentiment: {processed}/{total_valid} reviews có nội dung")

        return results


# PHẦN 3: PHÂN TÍCH KHÍA CẠNH (Aspect-Based Sentiment)

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


# PHẦN 4: HÀM TỔNG HỢP ĐỂ XỬ LÝ TOÀN BỘ REVIEWS

def enrich_reviews_with_nlp(reviews, output_path=None, batch_size=16, device=None):
    """
    Làm giàu danh sách reviews bằng cách thêm các cột sentiment và aspect.

    Hàm này nhận đầu vào là danh sách các dict review (output từ cleaning.clean_google_reviews),
    chạy mô hình PhoBERT để phân loại cảm xúc, trích xuất khía cạnh từ khóa,
    và trả về danh sách review đã được làm giàu.

    Args:
        reviews: Danh sách dict, mỗi dict chứa ít nhất trường 'review_text'.
        output_path: Đường dẫn file CSV đầu ra (tùy chọn). Nếu cung cấp, sẽ ghi kết quả ra file.
        batch_size: Kích thước batch khi chạy mô hình (mặc định 16).
        device: Thiết bị chạy mô hình ('cpu', 'cuda'). Mặc định tự động chọn.

    Returns:
        list[dict]: Danh sách reviews đã được bổ sung các trường:
            - cleaned_review_text: Văn bản đã tiền xử lý.
            - sentiment_label: Nhãn cảm xúc (Positive/Negative/Neutral).
            - sentiment_score: Điểm số xác suất của nhãn được chọn (0.0 - 1.0).
            - score_positive: Xác suất Positive.
            - score_negative: Xác suất Negative.
            - score_neutral: Xác suất Neutral.
            - aspect_service: True/False - Đề cập đến dịch vụ nhân viên.
            - aspect_price: True/False - Đề cập đến giá cả.
            - aspect_product: True/False - Đề cập đến chất lượng sản phẩm.
            - aspect_showroom: True/False - Đề cập đến không gian showroom.
            - aspect_delivery: True/False - Đề cập đến giao hàng/bảo hành.
    """
    if not reviews:
        print("[NLP] Không có review nào để xử lý.")
        return reviews

    print(f"[NLP] Bắt đầu xử lý NLP cho {len(reviews)} reviews...")

    # Bước 1: Khởi tạo mô hình PhoBERT
    analyzer = PhoBERTSentimentAnalyzer(batch_size=batch_size, device=device)

    # Bước 2: Tiền xử lý văn bản
    print("[NLP] Đang tiền xử lý văn bản...")
    raw_texts = [r.get("review_text", "") for r in reviews]
    cleaned_texts = [clean_text_for_nlp(t) for t in raw_texts]

    # Bước 3: Chạy phân tích cảm xúc theo batch
    print("[NLP] Đang chạy phân tích cảm xúc bằng PhoBERT...")
    sentiment_results = analyzer.predict_batch(raw_texts)

    # Bước 4: Trích xuất khía cạnh
    print("[NLP] Đang trích xuất khía cạnh từ khóa...")
    aspect_results = [extract_aspects(ct) for ct in cleaned_texts]

    # Bước 5: Gộp kết quả vào từng review
    enriched_reviews = []
    for i, review in enumerate(reviews):
        enriched = dict(review)  # Sao chép toàn bộ trường gốc

        # Thêm văn bản đã làm sạch
        enriched["cleaned_review_text"] = cleaned_texts[i]

        # Thêm kết quả sentiment
        sent = sentiment_results[i]
        rating = review.get("rating")
        review_text = review.get("review_text", "")
        
        # Nếu review không có text (hoặc trống sau khi clean) nhưng có rating, suy luận từ số sao
        is_empty_text = not review_text or not str(review_text).strip() or not cleaned_texts[i]
        
        if is_empty_text and rating is not None:
            try:
                rating_val = int(rating)
                if rating_val >= 4:
                    enriched["sentiment_label"] = "Positive"
                    enriched["sentiment_score"] = 1.0
                    enriched["score_positive"] = 1.0
                    enriched["score_negative"] = 0.0
                    enriched["score_neutral"] = 0.0
                elif rating_val <= 2:
                    enriched["sentiment_label"] = "Negative"
                    enriched["sentiment_score"] = 1.0
                    enriched["score_positive"] = 0.0
                    enriched["score_negative"] = 1.0
                    enriched["score_neutral"] = 0.0
                else:  # rating == 3
                    enriched["sentiment_label"] = "Neutral"
                    enriched["sentiment_score"] = 1.0
                    enriched["score_positive"] = 0.0
                    enriched["score_negative"] = 0.0
                    enriched["score_neutral"] = 1.0
            except (ValueError, TypeError):
                # Phòng hờ trường hợp không ép kiểu được rating
                enriched["sentiment_label"] = sent["sentiment_label"]
                enriched["sentiment_score"] = sent["sentiment_score"]
                enriched["score_positive"] = sent["all_scores"].get("Positive", 0.0)
                enriched["score_negative"] = sent["all_scores"].get("Negative", 0.0)
                enriched["score_neutral"] = sent["all_scores"].get("Neutral", 0.0)
        else:
            # Lấy kết quả từ mô hình PhoBERT
            enriched["sentiment_label"] = sent["sentiment_label"]
            enriched["sentiment_score"] = sent["sentiment_score"]
            enriched["score_positive"] = sent["all_scores"].get("Positive", 0.0)
            enriched["score_negative"] = sent["all_scores"].get("Negative", 0.0)
            enriched["score_neutral"] = sent["all_scores"].get("Neutral", 0.0)

        # Thêm kết quả aspect
        aspects = aspect_results[i]
        for aspect_name in ASPECT_KEYWORDS:
            enriched[aspect_name] = aspects.get(aspect_name, False)

        enriched_reviews.append(enriched)

    print(f"[NLP] Hoàn tất xử lý NLP cho {len(enriched_reviews)} reviews.")

    # Bước 6: Thống kê nhanh
    pos_count = sum(1 for r in enriched_reviews if r["sentiment_label"] == "Positive")
    neg_count = sum(1 for r in enriched_reviews if r["sentiment_label"] == "Negative")
    neu_count = sum(1 for r in enriched_reviews if r["sentiment_label"] == "Neutral")
    print(f"[NLP] Thống kê: Positive={pos_count}, Negative={neg_count}, Neutral={neu_count}")

    # Bước 7: Ghi ra file CSV nếu cần
    if output_path and enriched_reviews:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        headers = list(enriched_reviews[0].keys())
        with open(output_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(enriched_reviews)
        print(f"[NLP] Đã lưu kết quả tại: {output_path}")

    return enriched_reviews
