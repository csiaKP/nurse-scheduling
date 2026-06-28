from ortools.sat.python import cp_model
from config_manager import load_config
import pandas as pd
import os


def prepare_input_data():
    """
    [ฟังก์ชันที่ 1: เตรียมข้อมูล] 
    โหลดข้อมูลดิบจาก config_manager และแปลงค่าตัวแปรพร้อมใช้งาน
    """
    try:
        config_data = load_config()
        processed_data = {
            "num_days": config_data["num_days"],                            # จำนวนวันในเดือน (เช่น 31)
            "all_nurses": config_data["all_nurses"],                        # รายชื่อพยาบาลทั้งหมด
            "past_shifts": config_data["past_shifts"],                      # ประวัติเวรย้อนหลัง 3 วัน
            
            "min_off_days": config_data["min_off_days_required"],           # ค่าเริ่มต้นปกติคือ 11
            "max_off_days": config_data["max_off_days_required"],           # ค่าเริ่มต้นปกติคือ 12
            
            "daily_staffing_plan": config_data["daily_staffing_plan"],      
            
            "holiday_bookings": config_data.get("holiday_bookings", []),
            "nurse_10_custom_schedule": config_data.get("nurse_10_custom_schedule", {})
        }
        
        print("📊 [Status] เตรียมข้อมูลสำหรับจัดเวรเสร็จสิ้น สมบูรณ์ 100%")
        return processed_data

    except Exception as e:
        print(f"❌ [Error] เกิดข้อผิดพลาดในฟังก์ชันเตรียมข้อมูล: {e}")
        return None


def create_empty_schedule_variables(model, num_days, all_nurses):
    """
    [ขั้นตอนที่ 2: สร้างกล่อง]
    สร้างกล่องตัวแปร x[n, d, s] เปล่า ๆ ทิ้งไว้ในระบบ โดยยังไม่มีการเช็คเงื่อนไขใด ๆ ทั้งสิ้น
    """
    x = {}
    for n in all_nurses.keys():
        for d in range(num_days):
            for s in range(3):
                # s: 0=หยุด, 1=เช้า, 2=ดึก
                x[n, d, s] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')
                
    print(f"📦 [Status] สร้างกล่องตัวแปรเปล่าสำเร็จ: {len(x)} กล่อง")
    return x


def setup_status_helpers(x, past_shifts):
    """
    [ขั้นตอนที่ 3: ฟังก์ชันเช็คสถานะ]
    สร้างและส่งคืน (Return) ฟังก์ชัน get_shift_status และ is_working ไปใช้งานต่อ
    """
    def get_shift_status(nurse_id, day, shift_type):
        """
        เช็คสถานะกะรายวัน: ถ้าวันปัจจุบัน (>=0) ส่งคืนกล่องตัวแปร x ถ้าวันในอดีต (<0) ส่งคืนเลข 1/0 จากอดีต
        """
        if day >= 0:
            return x[nurse_id, day, shift_type]
        else:
            # ดึงประวัติเดือนเก่า: วันที่ -1 อยู่ Index 2, วันที่ -2 อยู่ Index 1, วันที่ -3 อยู่ Index 0
            history_index = day + 3
            history = past_shifts.get(nurse_id, [0, 0, 0])
            return 1 if history[history_index] == shift_type else 0

    def is_working(nurse_id, day):
        """
        เช็คว่าวันนั้นพยาบาลทำงานหรือไม่ (ทำงาน = ขึ้นเวรเช้า 1 หรือ เวรดึก 2)
        """
        return get_shift_status(nurse_id, day, 1) + get_shift_status(nurse_id, day, 2)

    # ทำการ Return ตัวช่วยทั้ง 2 ตัวออกไปใช้งานภายนอก
    return get_shift_status, is_working


def apply_basic_labor_constraints(model, num_days, all_nurses, get_shift_status, is_working):
    """
    [ขั้นตอนที่ 4: กฎเหล็ก]
    ผูกเงื่อนไขเฉพาะ 3 กฎเหล็กแกนหลัก: 1คน1กะ, ห้ามดึกต่อเช้า, และทำงาน 3 วันติดบังคับหยุด
    """
    for n in all_nurses.keys():
        if n == 13: continue  # ข้ามพยาบาลเบอร์ 13 ลาคลอด
        
        # 4.1 กฎ 1 คน 1 กะต่อวัน (ต้องเลือก หยุด หรือ เช้า หรือ ดึก อย่างใดอย่างหนึ่ง)
        for d in range(num_days):
            model.Add(get_shift_status(n, d, 0) + get_shift_status(n, d, 1) + get_shift_status(n, d, 2) == 1)
            
        # 4.2 กฎห้ามขึ้นเวรดึก (N) ต่อเวรเช้า (D) เด็ดขาด (เช็คตั้งแต่รอยต่อสิ้นเดือนเก่า d = -1)
        for d in range(-1, num_days - 1):
            model.Add(get_shift_status(n, d, 2) + get_shift_status(n, d + 1, 1) <= 1)
            
        # 4.3 กฎทำงานติดต่อกัน 3 วัน วันที่ 4 ต้องถูกบังคับให้ได้เวรหยุด (0) อัตโนมัติ
        for d in range(-3, num_days - 3):
            three_days_work = is_working(n, d) + is_working(n, d + 1) + is_working(n, d + 2)
            day_4_off = get_shift_status(n, d + 3, 0)
            
            # สมการ: ถ้า 3 วันแรกทำครบ (ยอดรวมเป็น 3) บีบให้ตัวแปรหยุดวันถัดไปเปิดเป็น 1 ทันที
            model.Add(three_days_work <= 2 + day_4_off)
            
    print("🚫 [Status] ผูกกฎเหล็กพื้นฐาน 3 ข้อแรกเรียบร้อยแล้ว")


# 5. soft constraints:


def create_solver_engine():
    """
    [ขั้นตอนที่ 6] เปิดเครื่องคำนวณและตั้งค่าพารามิเตอร์เบื้องต้น
    """
    solver = cp_model.CpSolver()
    # ตั้งค่าจำกัดเวลาคำนวณสูงสุด 30 วินาที เพื่อไม่ให้เว็บค้าง
    solver.parameters.max_time_in_seconds = 30.0
    return solver


def run_solver(solver, model, x, data):
    """
    [ขั้นตอนที่ 7] รับโมเดลที่มีกฎเหล็กครบแล้ว มาสั่งรันเพื่อผ่าทางตันหาคำตอบ
    """
    print("⏳ [Status] เครื่องยนต์กำลังเริ่มคำนวณจัดตารางเวร...")
    
    # สั่งรัน Solver โดยส่งโมเดลคณิตศาสตร์เข้าไปประมวลผล
    status = solver.Solve(model)
    
    # เช็คผลลัพธ์การรัน
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("✅ [Success] จัดตารางเวรพยาบาลสำเร็จลุล่วง!")
        return True, status
    else:
        print("❌ [Infeasible] ไม่สามารถจัดตารางได้! เงื่อนไขกฎเหล็กขัดแย้งกันเอง")
        return False, status


def run_schedule_pipeline():
    """
    [ฟังก์ชันหลักควบคุมระบบ] ทำหน้าที่เรียกใช้ทุกฟังก์ชันและส่งต่อ Parameter
    """
    # ขั้นตอนที่ 1: เตรียมเสบียงข้อมูล
    data = prepare_input_data()
    if not data: return "ข้อมูลไม่พร้อม"
    
    # ดึงค่าพื้นฐานมาเปิดลูป
    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    past_shifts = data["past_shifts"]
    
    # เปิดโมเดลคณิตศาสตร์หลักของ OR-Tools
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()
    
    # ขั้นตอนที่ 2: สั่งสร้างกล่องเปล่า (ได้กล่อง x กลับมา)
    x = create_empty_schedule_variables(model, num_days, all_nurses)
    
    # ขั้นตอนที่ 3: สั่งสร้างตัวช่วยเช็คสถานะ (ได้ฟังก์ชัน get_shift_status และ is_working กลับมา)
    get_shift_status, is_working = setup_status_helpers(x, past_shifts)
    
    # ขั้นตอนที่ 4: สั่งผูกกฎเหล็กต่าง ๆ เข้าไปใน model (ส่งตัวช่วยจากข้อ 3 เข้าไปด้วย)
    apply_basic_labor_constraints(model, num_days, all_nurses, get_shift_status, is_working)
    apply_nurse_off_bounds_constraints(model, num_days, all_nurses, get_shift_status)
    # (เรียกกฎเหล็กข้ออื่น ๆ เพิ่มตรงนี้...)
    
    # ขั้นตอนที่ 5: กฎรอง (ถ้ามี)
    
    # ขั้นตอนที่ 6: สร้างตัว Solver
    solver = create_solver_engine()
    
    # ขั้นตอนที่ 7: 🚀 สั่งรัน Solver (ส่งพารามิเตอร์ทั้งหมดที่คุณเตรียมไว้ไปให้)
    success, status = run_solver(solver, model, x, data)
    
    # ขั้นตอนหลังจากนี้ (แกะผลลัพธ์ / ปริ้นเช็ค / เซฟลง Excel)
    if success:
        # พิมพ์ผลลัพธ์ หรือ คืนค่าตารางเวรออกไป
        print("🎉 ตารางพร้อมใช้งานแล้ว!")
        
    return success




