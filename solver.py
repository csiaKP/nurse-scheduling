from ortools.sat.python import cp_model
import config_manager
from hard_constrain import apply_all_hard_constraints
# from soft_constrain import apply_soft_constraints
from config_manager import load_config
from main_func import print_schedule_results
    

def setup_variables(model, data):
    """
    สร้างตัวแปรตัดสินใจ (Decision Variables) x[n, d, s] 
    """
    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    shift = [0,1,2]  
    
    x = {}
    for n in all_nurses:
        for d in range(1, num_days + 1):
            for s in shift:
                x[n, d, s] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')
            
    return x


def create_shift_helpers(x, past_shifts):
    """
    สร้างฟังก์ชัน Helper สำหรับตรวจสอบเวรรวมประวัติย้อนหลัง
    """
     
    def get_shift_status(n, d, s):

        if d >= 1: return x[n, d, s]
    
        if d <= 0:
             d = d + 2 
             return 1 if s == past_shifts[n][d] else  0  
            
            
    def is_working(n, d):

        if d <= 0:
            d = d + 2
            return 1 if past_shifts[n][d] != 0 else 0
        
        if d >= 1: return x[n, d, 1] + x[n, d, 2]


    return get_shift_status, is_working


class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
    """
    Callback Class สำหรับพิมพ์ผลลัพธ์ระหว่างการค้นหาคำตอบทั้งหมด
    """
    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        print(f"=============================")
        print(f"🌟 ค้นพบคำตอบที่ถูกต้องชุดที่: {self.__solution_count}")
        print(f"=============================")

    @property
    def solution_count(self):
        return self.__solution_count

def solve_model_all_solutions(model, x, data):
    """
    สั่งค้นหาคำตอบที่เป็นไปได้ทั้งหมดภายใต้กฎเหล็ก (All Solutions Mode)
    """
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    
    # รวมตัวแปรทั้งหมดส่งให้พิมพ์ผลลัพธ์
    variable_list = list(x.values())
    solution_printer = VarArraySolutionPrinter(variable_list)
    
    status = solver.Solve(model, solution_printer)
    print(f"\n🔍 ค้นพบตารางเวรที่เป็นไปได้ทั้งหมด: {solution_printer.solution_count} รูปแบบ")
    return solver, status


def solve_model(model, max_time=30.0):
    """
    สั่งประมวลผลโมเดลหลัก เพื่อค้นหาคำตอบที่ดีที่สุดเพียงคำตอบเดียว (Single Solution Mode)
    """
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    solver.parameters.log_search_progress = False  # แสดงล็อกระหว่างประมวลผล
    
    status = solver.Solve(model)
    return solver, status


def run_solver_pipeline(data , max_time=30.0):
    """
    ฟังก์ชัน Pipeline หลักที่จะถูกเรียกจาก main.py
    """
    # 1. ตั้งต้นโมเดล
    model = cp_model.CpModel()
    
    # 2. สร้างตัวแปรตัดสินใจ
    x = setup_variables(model, data)
    
    # 3. ดึงตัวช่วยคำนวณเวรย้อนหลัง
    get_shift_status, is_working = create_shift_helpers(x, data["past_shifts"])
    
    # 4. เรียกใช้กฎเหล็กจากไฟล์ hard_constrain.py

    apply_all_hard_constraints(model, x, data, get_shift_status, is_working)


    solver, status = solve_model(model, max_time=max_time)
        
    return solver, status, x


def print_schedule(solver, status, x, data):
    """
    พิมพ์ตารางเวรผลลัพธ์ออกมาแสดงบนหน้าจอคอนโซลอย่างสวยงาม 
    (ดึงอดีตต่อหัวตาราง พร้อมย้ายยอดสรุปคนขึ้นเวรไปต่อท้ายวันด้านล่างตารางทันที)
    """
    if status != cp_model.OPTIMAL and status != cp_model.FEASIBLE:
        print("\n❌ ไม่พบคำตอบที่สอดคล้องกับเงื่อนไขทั้งหมด (Infeasible/No Solution)")
        return

    num_days = data["num_days"]
    all_nurses = data["all_nurses"]
    past_shifts = data["past_shifts"]
    bookings = data["holiday_bookings"] 
    shift = [0, 1, 2]

    # หัวตาราง
    print(f"{'':<10} {"past ":<5}", end="")

    for i in range(1, num_days + 1):
        print(f" {i:02d} ",end="")
    print("\n")

    # รายละเอียดตารางเวรของพยาบาลแต่ละคน
    for nurse_id, name in all_nurses.items():

        nurse_info = f"{nurse_id}  {name}"
        print(f"{nurse_info:<10}", end="")

        # พิม past shifts
        print("  ", end="")
        for s in past_shifts[nurse_id]:
            if s == 0:
                print("x", end="")
            elif s == 1:
                print("d", end="")
            elif s == 2:
                print("n", end="")
        print("| ", end="")


        nurse_booking = bookings.get(nurse_id, {})
        sum_off = 0
        for d in range(1, num_days + 1):
            for s in shift:
                if solver.Value(x[nurse_id, d, s]) == 1:
                    if s == 0:
                        if d in nurse_booking: print(" R  ", end="")
                        else: print(" .  ", end="")
                    elif s == 1:
                        print(" d  ", end="")
                    elif s == 2:
                        print(" n  ", end="")

            if solver.Value(x[nurse_id, d, 0]) == 1:
                sum_off += 1

        print(f"| {sum_off:02d} ", end="")
        print("\n")




if __name__ == "__main__":

    print("--- 🏥 เริ่มระบบจัดเวรอัตโนมัติ ---")
    
    data = load_config()
    
    solver, status, x = run_solver_pipeline(data, max_time=30.0)
    
    print_schedule(solver, status, x, data)
    
