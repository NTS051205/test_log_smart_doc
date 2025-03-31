from flask import Flask, request, render_template, jsonify
import pandas as pd
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Bật CORS để API có thể gọi từ frontend

# Đường dẫn file log
FILE_PATH = "vncodelab_logs_update_21_2.csv"

# Xử lý dữ liệu log
def process_logs(room_id=None):
    # Đọc dữ liệu từ file CSV
    df = pd.read_csv(FILE_PATH, low_memory=False)

    # Chuyển timestamp thành datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.tz_localize(None)

    # Xác định tuần (bắt đầu từ thứ Hai)
    df["week"] = df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%Y-%m-%d"))

    # Lọc theo roomID (nếu có)
    if room_id:
        df = df[df["roomID"].astype(str) == str(room_id)]

    # Loại bỏ các log không liên quan
    df_filtered = df[~df["logType"].isin(["leaveRoom", "scrollPosition"])]

    # Tính khoảng thời gian giữa các hoạt động
    df_filtered["time_diff"] = df_filtered.groupby(["week", "userName"])["timestamp"].diff()

    # Tổng thời gian học theo tuần
    total_time_spent = df_filtered.groupby(["week", "userName"])["time_diff"].sum().dt.total_seconds()

    # Loại bỏ NaN
    total_time_spent_cleaned = total_time_spent.dropna()

    # Tính các phân vị (Q1, Q2, Q3) theo tuần
    weekly_quantiles = total_time_spent_cleaned.groupby(level=0).quantile([0.25, 0.50, 0.75]).unstack()

    def categorize_time_spent(week, time_spent):
        Q1 = weekly_quantiles.loc[week, 0.25] if week in weekly_quantiles.index else 0
        Q2 = weekly_quantiles.loc[week, 0.50] if week in weekly_quantiles.index else 0
        Q3 = weekly_quantiles.loc[week, 0.75] if week in weekly_quantiles.index else 0

        if time_spent <= Q1:
            return "Low"
        elif time_spent <= Q2:
            return "Medium-Low"
        elif time_spent <= Q3:
            return "Medium-High"
        else:
            return "High"

    # Tạo kết quả dạng JSON theo tuần
    output_json = {}
    for (week, user), time_spent in total_time_spent_cleaned.items():
        if week not in output_json:
            output_json[week] = {}
        output_json[week][user] = {
            "total_time_spent": int(time_spent),
            "hardworking_level": categorize_time_spent(week, time_spent)
        }

    return output_json

# API endpoint
@app.route("/api/hardworking", methods=["GET"])
def get_hardworking_data():
    room_id = request.args.get("roomID")
    data = process_logs(room_id=room_id)
    return jsonify(data)

# Route render giao diện web
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
