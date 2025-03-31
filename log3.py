from flask import Flask, request, render_template, jsonify
import pandas as pd
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Sử dụng đường dẫn tương đối
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "vncodelab_logs_update_21_2.csv")

def process_logs(room_id=None):
    try:
        # Đọc dữ liệu từ file CSV
        df = pd.read_csv(FILE_PATH, low_memory=False)

        # Chuyển đổi timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.tz_localize(None)

        # Kiểm tra xem dữ liệu có hợp lệ không
        if df["timestamp"].isna().all():
            return {}

        # Xác định tuần dựa trên timestamp đầu tiên
        start_date = df["timestamp"].min()
        df["week_number"] = ((df["timestamp"] - start_date).dt.days // 7) + 1
        df["week"] = df["week_number"].apply(lambda x: f"Tuần {x}")

        # Xử lý danh sách tuần đầy đủ để tránh thiếu tuần
        max_week = df["week_number"].max()
        all_weeks = [f"Tuần {i}" for i in range(1, int(max_week) + 1)]
        df["week"] = df["week"].astype("category").cat.set_categories(all_weeks)

        # Lọc theo roomID nếu có
        if room_id:
            df = df[df["roomID"].astype(str) == str(room_id)]

        # Lọc bỏ log không quan trọng
        df_filtered = df[~df["logType"].isin(["leaveRoom", "scrollPosition"])]

        # Tính khoảng thời gian giữa các lần truy cập của từng user
        df_filtered = df_filtered.sort_values(["week", "userName", "timestamp"])
        df_filtered["time_diff"] = df_filtered.groupby(["week", "userName"])["timestamp"].diff()

        # Xử lý NaN khi tính tổng thời gian
        df_filtered["time_diff"] = df_filtered["time_diff"].fillna(pd.Timedelta(seconds=0))
        total_time_spent = df_filtered.groupby(["week", "userName"])["time_diff"].sum()

        # Chuyển timedelta sang giây
        total_time_spent = total_time_spent.apply(lambda x: x.total_seconds())

        # Đảm bảo max_time không bị lỗi chia cho 0
        max_time = max(total_time_spent.max(), 1)

        # Chuẩn bị dữ liệu JSON để truyền vào template
        output_json = {user: {week: {"time_spent": 0, "color": 0} for week in all_weeks} for user in df["userName"].unique()}
        
        for (week, user), time_spent in total_time_spent.items():
            time_in_seconds = int(time_spent)
            color_intensity = min(max(time_in_seconds / max_time, 0.2), 1)

            output_json[user][week] = {
                "time_spent": time_in_seconds,
                "color": color_intensity
            }

        return output_json
    except Exception as e:
        print(f"Lỗi xử lý log: {e}")
        return {}

@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    room_id = None

    if request.method == "POST":
        room_id = request.form.get("roomID")
        data = process_logs(room_id=room_id)

    return render_template("index.html", data=data, room_id=room_id)

if __name__ == "__main__":
    app.run(debug=True)
