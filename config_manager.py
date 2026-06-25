import json
import os

CONFIG_FILE = "config.json"

def get_monthly_config():
    """ข้อมูลตั้งค่าเริ่มต้น กรณีที่ไม่มีไฟล์ config.json"""
    all_nurses = {
        2: "Pu", 3: "Am",  4: "Nun",  5: "Yong",
        6: "Dee", 7: "Nuch", 8: "Nan", 9: "Ben",
        10: "Jane", 11: "Ruk", 12: "Ja", 13: "Pond",
        14: "Por",   15: "Gee", 16: "May",   17: "Fah",
        18: "Katae"
    }

    num_days = 31 
    min_off_days_required = 11   

    daily_staffing_plan = {
        "default": [5, 6, 4]
    }

    nurse_levels = {
        2: 4, 3: 4, 4: 4, 
        5: 3, 6: 3, 7: 3, 
        8: 4, 9: 2, 10: 2, 
        11: 2, 12: 2, 13: 3, 
        14: 3, 15: 2, 16: 3, 
        17: 2, 18: 1
    }

    past_shifts = {
        2: [0, 0, 0],  
        3: [0, 1, 2],  
        4: [1, 2, 0],  
        5: [1, 0, 1],  
        6: [2, 2, 0],  
        7: [2, 2, 0],  
        8: [1, 1, 1],  
        9: [1, 0, 0],  
        10: [2, 0, 1], 
        11: [0, 0, 0], 
        12: [0, 1, 1], 
        13: [0, 0, 0], 
        14: [0, 1, 2], 
        15: [2, 0, 1], 
        16: [1, 1, 2], 
        17: [0, 0, 0], 
        18: [0, 2, 2]  
    }

    holiday_bookings = []

    nurse_10_custom_schedule = { 
        1: 2, 2: 2, 3: 0, 4: 0, 5: 1, 6: 2, 7: 2, 8: 0, 9: 0,
        10: 1, 11: 2, 12: 2, 13: 0, 14: 0, 15: 1, 16: 2, 17: 2, 18: 0, 19: 0,
        20: 1, 21: 2, 22: 2, 23: 0, 24: 0, 25: 1, 26: 2, 27: 2, 28: 0, 29: 0,
        30: 1, 31: 2
    }

    return {
        "all_nurses": all_nurses,
        "num_days": num_days, 
        "min_off_days_required": min_off_days_required,
        "nurse_levels": nurse_levels,
        "past_shifts": past_shifts,
        "holiday_bookings": holiday_bookings,
        "daily_staffing_plan": daily_staffing_plan,
        "nurse_10_custom_schedule": nurse_10_custom_schedule
    }


def load_config(config_path=CONFIG_FILE):
    """
    อ่านข้อมูล config จากไฟล์ JSON และแปลงประเภทของคีย์ข้อมูลให้อยู่ในรูปแบบที่ถูกต้องสำหรับ Python/OR-Tools
    """
    if not os.path.exists(config_path):
        print(f"⚠️ ไม่พบไฟล์ {config_path} ใช้ค่าเริ่มต้นแทน")
        return get_monthly_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_json = json.load(f)
        
        # แปลงข้อมูลใน Dictionary จาก String Key เป็น Integer Key
        data = {
            "all_nurses": {int(k): v for k, v in config_json.get("all_nurses", {}).items()},
            "num_days": config_json.get("num_days", 31),
            "min_off_days_required": config_json.get("min_off_days_required", 11),
            "nurse_levels": {int(k): v for k, v in config_json.get("nurse_levels", {}).items()},
            "past_shifts": {int(k): v for k, v in config_json.get("past_shifts", {}).items()},
            "daily_staffing_plan": {
                ("default" if k == "default" else int(k)): v 
                for k, v in config_json.get("daily_staffing_plan", {}).items()
            },
            "holiday_bookings": [
                (tuple(item) if isinstance(item, list) else item) 
                for item in config_json.get("holiday_bookings", [])
            ],
            "nurse_10_custom_schedule": {
                int(k): v for k, v in config_json.get("nurse_10_custom_schedule", {}).items()
            }
        }
        return data
    except Exception as e:
        print(f"❌ ผิดพลาดในการอ่าน {config_path}: {e}")
        return get_monthly_config()


def load_nurses_list(config_path=CONFIG_FILE):
    """ดึงรายชื่อพยาบาล"""
    data = load_config(config_path)
    return data["all_nurses"]


def load_bookings(config_path=CONFIG_FILE):
    """ดึงข้อมูล holiday_bookings ทั้งหมด"""
    try:
        if not os.path.exists(config_path):
            return []
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("holiday_bookings", [])
    except Exception as e:
        print(f"❌ ไม่สามารถอ่านรายการจองวันหยุด: {e}")
        return []


def save_bookings(bookings, config_path=CONFIG_FILE):
    """บันทึกข้อมูล holiday_bookings กลับลงไฟล์ JSON โดยไม่เปลี่ยนค่าอื่น ๆ"""
    try:
        # โหลดข้อมูลดิบในปัจจุบัน
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # แปลง get_monthly_config คีย์ที่เป็น int กลับเป็น string ก่อนเซฟ เพื่อความถูกต้องของ JSON
            raw_data = get_monthly_config()
            data = {
                "all_nurses": {str(k): v for k, v in raw_data["all_nurses"].items()},
                "num_days": raw_data["num_days"],
                "min_off_days_required": raw_data["min_off_days_required"],
                "nurse_levels": {str(k): v for k, v in raw_data["nurse_levels"].items()},
                "past_shifts": {str(k): v for k, v in raw_data["past_shifts"].items()},
                "daily_staffing_plan": {str(k): v for k, v in raw_data["daily_staffing_plan"].items()},
                "holiday_bookings": [],
                "nurse_10_custom_schedule": {str(k): v for k, v in raw_data["nurse_10_custom_schedule"].items()}
            }

        # บันทึกข้อมูลการจองโดยแปลง tuple เป็น list
        json_bookings = []
        for b in bookings:
            if isinstance(b, (list, tuple)):
                json_bookings.append([int(x) for x in b])
            else:
                json_bookings.append(b)

        data["holiday_bookings"] = json_bookings

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ ไม่สามารถบันทึกรายการจองวันหยุด: {e}")
        return False


if __name__ == '__main__':
    # ส่วนสำหรับทดสอบรันไฟล์ตัวกลางโดยตรง
    print("🔍 ทดสอบการรันไฟล์ config_manager.py...")
    config = load_config()
    print(f"✅ โหลดข้อมูลสำเร็จ! มีรายชื่อพยาบาลทั้งหมด {len(config['all_nurses'])} คน")
    bookings = load_bookings()
    print(f"✅ โหลดการจองสำเร็จ! มีข้อมูลการจอง {len(bookings)} รายการ")
