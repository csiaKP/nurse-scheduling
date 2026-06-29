from ortools.sat.python import cp_model
import pandas as pd
import os
from config_manager import load_config  


# กล่องที่ 2: ฟังก์ชันตัวช่วยดึงประวัติเวรเก่า (Helpers)
def create_shift_helpers(x, past_shifts):
    def get_shift_status(nurse, day_idx, shift_type):
        if day_idx < 0:
            return 1 if past_shifts[nurse][day_idx + 3] == shift_type else 0
        return x[nurse, day_idx, shift_type]

    def is_working(nurse, day_idx):
        if day_idx < 0:
            return 1 if past_shifts[nurse][day_idx + 3] in (1, 2) else 0
        return x[nurse, day_idx, 1] + x[nurse, day_idx, 2]
        
    return get_shift_status, is_working


# กล่องที่ 3.1: กฎเหล็กพยาบาลทั่วไปทุกคน
def apply_general_hard_constraints(model, x, data, get_shift_status, is_working):
    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    min_off_days_required = data["min_off_days_required"]
    nurse_levels = data["nurse_levels"]
    shifts = list((0, 1, 2))

    # 📌 กฎพื้นฐาน: 1 วัน พนักงานทุกคนต้องได้ 1 กะ เท่านั้น
    for n in all_nurses.keys():
        for d in range(num_days):
            model.Add(sum(x[n, d, s] for s in shifts) == 1)

    # 📌 กฎเหล็กควบคุมพยาบาลทุกคนที่มาปฏิบัติงานจริง  (ยกเว้นคนลาคลอดเบอร์ 13)
    for n in all_nurses.keys():
        if n != 13:
            # ล็อกจำนวนวันหยุดประจำเดือน (11-12 วัน) สำหรับพยาบาลทั่วไป (ยกเว้นคุณเจนเบอร์ 10)
            if n != 10 and n != 3 and n!= 12:
                model.Add(sum(x[n, d, 0] for d in range(num_days)) == min_off_days_required)
                # model.Add(sum(x[n, d, 0] for d in range(num_days)) <= 12)

            # if  n == 3 and n == 12 :
            #     model.Add(sum(x[n, d, 0] for d in range(num_days)) == 12)

            # ห้ามขึ้นเวร ดึก ต่อ เช้า (N -> D) เด็ดขาด
            for d in range(-1, num_days - 1):
                model.Add(get_shift_status(n, d, 2) + get_shift_status(n, d + 1, 1) <= 1)

            # ทำงานติดต่อกันห้ามเกิน 3 วันเด็ดขาด
            for d in range(-3, num_days - 3):
                model.Add(is_working(n, d) + is_working(n, d + 1) + is_working(n, d + 2) + is_working(n, d + 3) < 4)


    #📌 ควบคุมจำนวนคนขึ้นเวรรายวัน (ดึงแผนผังยืดหยุ่นรายวันจากส่วนเตรียมข้อมูล)
    plan = data["daily_staffing_plan"]
    for d in range(num_days):
        actual_day = d + 1
        min_day, max_day, exact_night = plan[actual_day] if actual_day in plan else plan["default"]

        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) >= min_day) 
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) <= max_day)
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys()) >= exact_night)
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys()) <= 5)
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) - sum(x[n, d, 2] for n in all_nurses.keys()) <= 1)

        # บังคับต้องมีหัวหน้าเวร (LV2) อย่างน้อยกะละ 1 คนทุกวัน
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys() if nurse_levels[n] >= 2) >= 1) 
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys() if nurse_levels[n] >= 2) >= 1)
    
    
    # 3. คิวจองวันหยุดล่วงหน้า R1-R3 ของพยาบาลคนอื่นๆ (ปิดไม่ให้ระบบออโต้ไปทับตารางคุณเจน)
    for nurse, actual_day, queue_order in data["holiday_bookings"]:
        if queue_order <= 4 : 
            day_idx = actual_day - 1 
            model.Add(x[nurse, day_idx, 0] == 1) 
            model.Add(x[nurse, day_idx, 1] == 0) 
            model.Add(x[nurse, day_idx, 2] == 0)
    
    
    for n in [5,8,14]:
        model.Add(sum(x[n, d, 1] for d in range(num_days)) <= 16)
    
    model.Add(sum(x[12, d, 2] for d in range(num_days)) == 0)


# กล่องที่ 3.2: กฎล็อกเวรคนลาคลอด (เบอร์ 13)
def apply_maternity_leave_constraints(model, x, data):
    num_days = data["num_days"]
    
    # 📌 พยาบาลเบอร์ 13 บังคับให้สวิตช์กะหยุด (0) เป็นจริงทุกวัน ตลอดทั้ง 31 วัน
    for d in range(num_days):
        model.Add(x[13, d, 0] == 1) # เปิดกะหยุด
        model.Add(x[13, d, 1] == 0) # ห้ามเวรเช้า
        model.Add(x[13, d, 2] == 0) # ห้ามเวรดึก


# กล่องที่ 3.3: กฎล็อกเวรของคุณเจน
def apply_jane_constraints(model, x, data):
    num_days = data["num_days"]
    shifts = list((0, 1, 2))

    if 10 in data["all_nurses"]:
        # 1. บังคับคุณเจน (เบอร์ 10) ได้วันหยุด 12 วันเป๊ะๆ ตามโควตา
        model.Add(sum(x[10, d, 0] for d in range(num_days)) == 12)

        # 2. ล็อกตารางเวรคุณเจนตามปฏิทินที่กำหนดล่วงหน้า (รวมแบบปกติ + แบบความลับ Secret)
        full_jane_schedule = data["nurse_10_custom_schedule"]
        for actual_day, required_shift in full_jane_schedule.items():
            day_idx = actual_day - 1
            for s in shifts:
                if s == required_shift:
                    model.Add(x[10, day_idx, s] == 1)
                else:
                    model.Add(x[10, day_idx, s] == 0)


# กล่องที่ 4: กล่องใส่กฎรองเพื่อคิดคะแนนรางวัล (Soft Constraints)
def apply_soft_constraints(model, x, data):
    target_scores = []
    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    

    # คะแนนคิวจองวันหยุด
    for nurse, actual_day, queue_order in data["holiday_bookings"]:
            day_idx = actual_day - 1 
            weight = 1000 - (queue_order * 10)
            target_scores.append(x[nurse, day_idx, 0] * weight)


            
    # บีบให้หยุด 11 วันเป็นหลัก ใครได้ 12 วัน โดนลบคะแนนหนัก
    active_nurses = [n for n in all_nurses.keys() if n != 13 and n != 10]
    for n in active_nurses:
        total_off_days = sum(x[n, d, 0] for d in range(num_days))
        target_scores.append(total_off_days * -5000) 


    # แจกคะแนนจูงใจให้เกลี่ยเวรเช้า (d) กระจายตัว
    # for d in range(num_days):
    #     daily_day_shift_total = sum(x[n, d, 1] for n in all_nurses.keys())
    #     target_scores.append(daily_day_shift_total * 10)

    # for d in range(num_days):
    #     daily_day_shift_total = sum(x[n, d, 2] for n in all_nurses.keys())
    #     target_scores.append(daily_day_shift_total * 100)


    reward = 50
    # pennalty = -22
    
    for nurse in [5,8,12,14]:
        total_morning_days = sum(x[nurse, d, 1] for d in range(num_days))
        target_scores.append(total_morning_days * reward)


    if target_scores:
        model.Maximize(sum(target_scores))


# กล่องที่ 5: (Solver)
def solve_model(model, max_time=30.0):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    status = solver.Solve(model)
    return solver, status


# กล่องที่ 6b: พิมพ์ผลลัพธ์ออกหน้าจอ (Console-friendly)
def print_schedule_results(solver, status, x, data):
    formatted_data = format_schedule_data(solver, status, x, data)
    
    if not formatted_data["success"]:
        print(formatted_data["message"])
        return
    
    print(f"=== 🎉 {formatted_data['message']} (วันที่ 1 ถึง 31) ===\n")
    print(f"No  Name            Past    {' '.join(f'{d:02d}' for d in range(1, 32))} | หยุดจริง")
    print("-" * 140)
    
    for item in formatted_data["schedule"]:
        shifts_str = " ".join(f" {s} " for s in item["shifts"])
        comment = f" {item['comment']}" if item['comment'] else ""
        print(f"{item['nurse_id']:02d}  {item['name']:<15} [{item['past']}]  {shifts_str} |   {item['off_days']:02d} วัน{comment}")
    
    print("\n" + "="*140)
    print("📊 สรุปจำนวนคนทำงานจริงในแต่ละวัน")
    print("="*140)
    print("วันที่:         " + "  ".join(f"{d:02d}" for d in range(1, 32)))
    print("เวรเช้า (d):  " + "".join(f" {c:<3}" for c in formatted_data["summary"]["day_totals"]))
    print("เวรดึก (n):   " + "".join(f" {c:<3}" for c in formatted_data["summary"]["night_totals"]))
    print("=" * 140)


# (Variables Setup) สร้างกล่อง x [ ]
def setup_variables(model, data):
    shifts = list((0, 1, 2))  
    num_days = data["num_days"]
    
    x = {}
    for n in data["all_nurses"].keys(): 
        for d in range(num_days):
            for s in shifts:
                x[n, d, s] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')
                
    return x  # ส่งตู้เอกสาร x ที่ใส่แคปซูลครบแล้วกลับไปให้คนเรียกใช้งาน


#Save to excel
def save_schedule_to_excel(solver, status, x, data, filename="schedule_results.xlsx"):
    
    if status != 1 and status != 4: # เช็กว่าจัดสำเร็จไหม
        print("❌ จัดตารางไม่สำเร็จ ไม่สามารถบันทึก Excel ได้")
        return

    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    past_shifts = data["past_shifts"]
    holiday_bookings = data["holiday_bookings"]

    rows = []
    
    # 1. ดึงข้อมูลรายคนใส่ตาราง
    for n, name in all_nurses.items():
        past_str = "".join("d" if s==1 else ("n" if s==2 else "x") for s in past_shifts[n])
        nurse_row = {"No": f"{n:02d}", "Name": name, "Past": f"[{past_str}]"}
        
        actual_off = 0
        for d in range(num_days):
            day_num = d + 1
            if solver.Value(x[n, d, 1]) == 1:
                nurse_row[str(day_num)] = "d"
            elif solver.Value(x[n, d, 2]) == 1:
                nurse_row[str(day_num)] = "n"
            else:
                is_booked_r = any(nurse == n and actual_day == day_num for nurse, actual_day, queue_order in holiday_bookings)
                nurse_row[str(day_num)] = "R" if is_booked_r else "-"
                actual_off += 1
                
        nurse_row["หยุดจริง"] = f"{actual_off:02d} "
        nurse_row["หมายเหตุ"] = " (ลาคลอด)" if n == 13 else ""
        rows.append(nurse_row)

    # 2. ดึงยอดสรุปจำนวนคนรายวันมาต่อท้ายตาราง
    day_totals_row = {"No": "", "Name": "📊 เวรเช้า (d)", "Past": "", "หยุดจริง": "", "หมายเหตุ": ""}
    night_totals_row = {"No": "", "Name": "📊 เวรดึก (n)", "Past": "", "หยุดจริง": "", "หมายเหตุ": ""}
    for d in range(num_days):
        day_num = d + 1
        day_totals_row[str(day_num)] = sum(solver.Value(x[n, d, 1]) for n in all_nurses.keys())
        night_totals_row[str(day_num)] = sum(solver.Value(x[n, d, 2]) for n in all_nurses.keys())
    rows.append(day_totals_row)
    rows.append(night_totals_row)

    # 3. แปลงเป็น DataFrame และเซฟไฟล์
    df = pd.DataFrame(rows)
    date_columns = [str(d) for d in range(1, num_days + 1)]
    final_columns = ["No", "Name", "Past"] + date_columns + ["หยุดจริง", "หมายเหตุ"]
    df[final_columns].to_excel(filename, index=False)
    print(f"💾 บันทึกไฟล์ Excel สำเร็จในชื่อ: {filename}")


# 7. ฟังก์ชันหลัก (Main Control Pipeline) และคำสั่งรันระบบ
def run_nurse_scheduling(config_path="config.json"):
    
    # สั่งเปิดโมเดลคณิตศาสตร์ตัวหลัก
    model = cp_model.CpModel()
    
    data = load_config(config_path)

    x = setup_variables(model, data)

    get_shift_status, is_working = create_shift_helpers(x, data["past_shifts"])

    apply_general_hard_constraints(model, x, data, get_shift_status, is_working)
    apply_maternity_leave_constraints(model, x, data)
    apply_jane_constraints(model, x, data)
    
    apply_soft_constraints(model, x, data)
    
    solver, status = solve_model(model, max_time=60.0)
    
    print_schedule_results(solver, status, x, data)
    
    return solver, status, x, data


if __name__ == '__main__':
    run_nurse_scheduling()
