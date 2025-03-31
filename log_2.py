from flask import Flask, request, render_template, jsonify
import pandas as pd
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Đường dẫn file CSV
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

    # Chuyển dữ liệu thành dictionary để render trên web
    output_json = {}
    for (week, user), time_spent in total_time_spent_cleaned.items():
        if user not in output_json:
            output_json[user] = {}
        output_json[user][week] = int(time_spent)

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
