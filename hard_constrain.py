
def apply_all_hard_constraints(model, x, data, get_shift_status, is_working):
    """
    [Master Function] ฟังก์ชันหลักที่เป็นศูนย์รวม 
    ทำหน้าที่เรียกใช้งานกฎเหล็กย่อยทั้ง 7 ข้อเรียงตามลำดับ
    """

    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    
    # กลุ่มที่ 1: กฎควบคุมกำลังพลรวมระดับวอร์ด
    apply_one_shift_per_day(model, x, data, num_days, all_nurses)
    
    
    # apply_night_day_continue(model, x, data, num_days, all_nurses, get_shift_status)  
    # apply_work_limit(model, x, data, num_days, all_nurses, is_working)
    

    apply_daily_staff_demand(model, x, data, num_days)
    

    # กลุ่มที่ 3: กฎตามเงื่อนไขพิเศษและสิทธิวันหยุด
    # apply_holiday_bookings(model, x, data)
    # apply_monthly_off_days_requirement(model, x, data, num_days, all_nurses)
    # apply_like_day(model, x, data, num_days, xxx )
    # apply_leave_requests(model, x, data, num_days , xxx)
    # apply_jane(model, x, data, num_days, xxx)    



# =========================================================================
# รายชื่อฟังก์ชันย่อยทั้ง 7 ข้อ (โครงสร้างเปล่าสำหรับรอใส่รายละเอียดกฎเหล็ก)
# =========================================================================


def apply_one_shift_per_day(model, x, data, num_days, all_nurses):
    """[กฎข้อที่ 2] พยาบาล 1 คน สามารถขึ้นเวรได้มากที่สุดเพียง 1 เวรต่อ 1 วัน"""

    shift = [0, 1, 2]  # เวรที่อนุญาตให้พยาบาลทำงานได้ (0=Off, 1=Day, 2=Night)
    for n in all_nurses:
        for d in range(1,num_days+1):
            model.Add(sum(x[n, d, s] for s in shift) == 1)


def apply_night_day_continue(model, x, data, num_days, all_nurses, get_shift_status):
    """[กฎข้อที่ 4] ห้ามลงดึกต่อเช้า"""
    pass


def apply_work_limit(model, x, data, num_days, all_nurses, is_working):
    """[กฎข้อที่ 3] ควบคุมไม่ให้พยาบาลทำงานติดต่อกันเกินจำนวนวันที่กำหนด (เช่น ห้ามเกิน 3 วัน)"""
    pass



def apply_daily_staff_demand(model, x, data, num_days):
    """[กฎข้อที่ 1] ควบคุมจำนวนพยาบาลในแต่ละเวรให้ตรงตามแผนรายวัน (min, max, exact)"""

    all_nurses = data["all_nurses"]
    plan = data["daily_staffing_plan"]
    nurse_levels = data["nurse_levels"]


    # 1. เช็กว่าวันนั้น ๆ มีแผนพิเศษไหม ถ้าไม่มีให้ใช้ค่า default
    min_day, max_day, min_night, max_night = plan["default"]


    for d in range(1, num_days + 1):


        # 2. บังคับจำนวนคนขึ้นเวรเช้า (กะ 1)
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) >= min_day)
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) <= max_day)
        
        # 3. บังคับจำนวนคนขึ้นเวรดึก (กะ 2)
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys()) >= min_night)
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys()) <= max_night)
        
        # 4. กฎเหล็กแฝง: บังคับเวรเช้าห้ามห่างจากเวรดึกเกิน 1 คน (ตามโค้ดเดิมของคุณ)
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys()) - sum(x[n, d, 2] for n in all_nurses.keys()) <= 1)
        
        # 5. กฎเหล็กแฝง: บังคับต้องมีหัวหน้าเวร (LV2 ขึ้นไป) อย่างน้อยกะละ 1 คนทุกวัน
        model.Add(sum(x[n, d, 1] for n in all_nurses.keys() if nurse_levels[n] >= 2) >= 1)
        model.Add(sum(x[n, d, 2] for n in all_nurses.keys() if nurse_levels[n] >= 2) >= 1)



def apply_holiday_bookings(model, x, data):
    """[กฎข้อที่ 5] ล็อกวันหยุดตามที่พยาบาลแต่ละคนได้ทำเรื่องจอง/ลาล่วงหน้าไว้"""
    pass


def apply_monthly_off_days_requirement(model, x, data, num_days, all_nurses):
    """[กฎข้อที่ 6] บังคับจำนวนวันหยุดขั้นต่ำรวมทั้งเดือนที่พยาบาลแต่ละคนต้องได้รับ"""
    pass


def apply_like_day(model, x, data, num_days, xxx):
    """[กฎข้อที่ 7] ชอบเวรเช้า"""
    pass

def apply_leave_requests(model, x, data, num_days, xxx):
    """[กฎข้อที่ 8] ลาทั้งเดือน"""
    pass

def apply_jane(model, x, data, num_days, xxx):
    """"[กฎข้อที่ 9] เจนคือคนพิเศษ"""
    pass
