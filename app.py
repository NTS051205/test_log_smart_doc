from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

MONGO_URI = "mongodb://codelab1:neucodelab@101.96.66.219:8000/?authMechanism=SCRAM-SHA-1"
client = MongoClient(MONGO_URI)
db = client["vncodelab"]
collection = db["logs"]

def process_logs(df):
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    cutoff_date = pd.Timestamp("2025-02-19")
    start_date = pd.Timestamp("2024-12-23")

    df["user_display"] = df.apply(
        lambda row: row["user"] if row["timestamp"] < cutoff_date else row["userName"], axis=1
    )

    df = df[df["logType"] != "leaveRoom"]

    df = df.sort_values(["user_display", "timestamp"])

    df["time_diff"] = df.groupby("user_display")["timestamp"].diff()

    df["custom_week"] = ((df["timestamp"] - start_date).dt.days // 7) + 1

    df["time_diff_seconds"] = df["time_diff"].dt.total_seconds()

    max_diff = 800 
    df["time_diff_seconds"] = df["time_diff_seconds"].apply(
        lambda x: x if (x is not None and x > 0 and x <= max_diff) else 0
    )

    study_time_per_week = df.groupby(["user_display", "custom_week"])["time_diff_seconds"].sum()

    activity_per_week = df.groupby(["user_display", "custom_week"])["timestamp"].count()

    max_activity_per_week = activity_per_week.groupby("custom_week").max()

    max_activity_series = pd.Series(index=activity_per_week.index)
    for week in activity_per_week.index.get_level_values('custom_week').unique():
        max_val = max_activity_per_week.loc[week]
        idx = activity_per_week.index[activity_per_week.index.get_level_values('custom_week') == week]
        max_activity_series.loc[idx] = max_val

    hardworking_score = (activity_per_week / max_activity_series) * 100

    study_time_q1 = study_time_per_week.groupby("custom_week").quantile(0.25)
    study_time_q3 = study_time_per_week.groupby("custom_week").quantile(0.75)
    study_time_min = study_time_per_week.groupby("custom_week").min()
    study_time_iqr = study_time_q3 - study_time_q1

    hardworking_q1 = hardworking_score.groupby("custom_week").quantile(0.25)
    hardworking_q3 = hardworking_score.groupby("custom_week").quantile(0.75)
    hardworking_min = hardworking_score.groupby("custom_week").min()
    hardworking_iqr = hardworking_q3 - hardworking_q1

    study_time_threshold = study_time_min.combine(study_time_q1 - study_time_iqr, min)
    hardworking_threshold = hardworking_min.combine(hardworking_q1 - hardworking_iqr, min)

    attendance_criteria = pd.DataFrame({
        "Total Study Time (s)": study_time_per_week,
        "Hardworking Score": hardworking_score
    }).reset_index()

    attendance_criteria["Attendance"] = attendance_criteria.apply(
        lambda row: "✓" if row["Total Study Time (s)"] >= study_time_threshold.get(row["custom_week"], 0) and 
                        row["Hardworking Score"] >= hardworking_threshold.get(row["custom_week"], 0) 
                else "", axis=1
    )

    weekly_attendance = attendance_criteria.pivot(index="user_display", columns="custom_week", values="Attendance")

    return weekly_attendance.to_dict()

@app.route("/api/hardworking2", methods=["GET"])
def get_hardworking_data2():
    room_id = request.args.get("roomID")
    if not room_id:
        return jsonify({"error": "Thiếu roomID"}), 400

    data = list(collection.find({"roomID": room_id}, {"_id": 0}))  

    print("Dữ liệu từ MongoDB:", data)

    df = pd.DataFrame(data)
    if df.empty:
        return jsonify({})

    return jsonify(process_logs(df))

if __name__ == "__main__":
    app.run(debug=True)
