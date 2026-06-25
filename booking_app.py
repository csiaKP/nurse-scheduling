from flask import Flask, render_template, request, jsonify
from config_manager import load_nurses_list, load_bookings, save_bookings

app = Flask(__name__)

# ===== ROUTES =====

@app.route('/')
def index():
    """หน้าหลัก - แสดงฟอร์มจองวันหยุด"""
    nurses = load_nurses_list()
    bookings = load_bookings()
    return render_template('booking.html', nurses=nurses, bookings=bookings)


@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """API: ดึงข้อมูล holiday bookings ทั้งหมด"""
    bookings = load_bookings()
    return jsonify({"success": True, "bookings": bookings})


@app.route('/api/bookings/save', methods=['POST'])
def save_all_bookings():
    """API: บันทึก holiday bookings ด้วยวิธี Diff (เพิ่ม/ลบเฉพาะรายบุคคล)"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "❌ ไม่มีข้อมูลส่งมา"}), 400
        
    added = data.get('added', [])
    deleted = data.get('deleted', [])
    
    # ดึง nurse_id ทั้งหมดเพื่อตรวจสอบความปลอดภัย (ต้องแก้ไขทีละคนใน 1 คำขอ)
    nurse_ids = set()
    for item in added:
        if 'nurse_id' in item:
            nurse_ids.add(int(item['nurse_id']))
    for item in deleted:
        if 'nurse_id' in item:
            nurse_ids.add(int(item['nurse_id']))
            
    if len(nurse_ids) == 0:
        return jsonify({"success": True, "message": "✅ ไม่มีการเปลี่ยนแปลงที่ต้องบันทึก", "bookings": load_bookings()})
        
    # if len(nurse_ids) > 1:
    #     return jsonify({"success": False, "message": "❌ ปฏิเสธการบันทึก: กรุณาแก้ไขและกดบันทึกข้อมูลของพยาบาลทีละคนเท่านั้น"}), 400
        
    target_nurse_id = list(nurse_ids)[0]
    
    # โหลดข้อมูลจองเวรทั้งหมดในปัจจุบันจาก config.json แบบเรียลไทม์
    current_bookings = load_bookings()
    
    # วันที่ได้รับการแก้ไข (เพื่อใช้นำมาปรับเรียงคิว R)
    modified_days = set()
    
    # 1. จัดการข้อมูลลบ (Delete)
    for item in deleted:
        n_id = int(item['nurse_id'])
        day = int(item['day'])
        modified_days.add(day)
        # ลบการจองเดิมออก
        current_bookings = [b for b in current_bookings if not (int(b[0]) == n_id and int(b[1]) == day)]
        
    # 2. จัดการข้อมูลเพิ่ม (Add)
    for item in added:
        n_id = int(item['nurse_id'])
        day = int(item['day'])
        modified_days.add(day)
        # ตรวจสอบก่อนว่าเคยจองไปแล้วหรือยัง (ป้องกันการจองซ้ำวัน)
        if any(int(b[0]) == n_id and int(b[1]) == day for b in current_bookings):
            continue
        # ให้ R คิวจำลองเป็นค่าเยอะ ๆ ก่อน เดี๋ยวจะนำไปจัดเรียงคิว R จริงในขั้นตอนถัดไป
        current_bookings.append([n_id, day, 999])
        
    # 3. จัดการคิว R ใหม่สำหรับวันที่ได้รับการแก้ไข (Auto-shift R)
    for day in modified_days:
        day_bookings = [b for b in current_bookings if int(b[1]) == day]
        other_bookings = [b for b in current_bookings if int(b[1]) != day]
        
        # จัดเรียงตามคิวเดิม (คนใหม่ที่ 999 จะอยู่ท้ายสุด)
        day_bookings.sort(key=lambda x: int(x[2]))
        
        # รันจัดลำดับคิว R ใหม่ตั้งแต่ 1 ถึง N
        new_day_bookings = []
        for i, b in enumerate(day_bookings):
            new_day_bookings.append([int(b[0]), int(b[1]), i + 1])
            
        # รวมข้อมูลกลับคืน
        current_bookings = other_bookings + new_day_bookings

    # 4. ตรวจสอบเงื่อนไขจำนวนวันจองรวมของพยาบาลคนนี้ (ต้องไม่เกิน 5 วัน)
    nurse_total_bookings = [b for b in current_bookings if int(b[0]) == target_nurse_id]
    if len(nurse_total_bookings) > 5:
        return jsonify({"success": False, "message": f"❌ ปฏิเสธการบันทึก: พยาบาลคนนี้เลือกวันหยุดรวมเกินโควตา 5 วัน"}), 400

    # บันทึกข้อมูลลง config.json
    success = save_bookings(current_bookings)
    if success:
        return jsonify({
            "success": True, 
            "message": "✅ บันทึกการเปลี่ยนแปลงและคำนวณเรียงคิว R ใหม่สำเร็จ!",
            "bookings": current_bookings
        })
    else:
        return jsonify({"success": False, "message": "❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล"}), 500


@app.route('/api/nurses', methods=['GET'])
def get_nurses():
    """API: ดึงรายชื่อพยาบาล"""
    nurses = load_nurses_list()
    return jsonify({"success": True, "nurses": nurses})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
