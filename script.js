const nursesData = window.FlaskData.nurses;
const initialBookings = window.FlaskData.bookings;

let currentBookings = JSON.parse(JSON.stringify(initialBookings));
let addedChanges = [];
let deletedChanges = [];
let activeNurseId = null;

window.onload = function() {
    renderDaysHeader();
    renderCalendar();
    updateStats();
};


function renderDaysHeader() {
    const headerRow = document.getElementById('calendar-header-row');
    for (let d = 1; d <= 31; d++) {
        const th = document.createElement('th');
        th.innerText = d;
        headerRow.appendChild(th);
    }
}


function renderCalendar() {
    const tbody = document.getElementById('calendar-body');
    tbody.innerHTML = '';

    // ตรวจสอบและแปลงร่างข้อมูล: ถ้าหลังบ้านส่งมาเป็น Dict ปีกกา ให้แปลงเป็น List ก่อนวนลูป
    const nursesList = Array.isArray(nursesData) 
        ? nursesData 
        : Object.entries(nursesData).map(([id, name]) => [parseInt(id), name]);

    // นำรายชื่อที่แปลงเสร็จแล้วมาวาดตาราง
    nursesList.forEach(nurse => {
        const nId = parseInt(nurse[0]); // ดึงหมายเลขพยาบาลจริงจาก JSON (เช่น 2, 3, 4)
        const nName = nurse[1]; 

        const tr = document.createElement('tr');

        // 1. สร้างช่องคอลัมน์หมายเลขพยาบาล (ดึงค่า nId มาแสดงตรงๆ)
        const noTd = document.createElement('td');
        noTd.innerText = nId; 
        noTd.style.textAlign = 'center';
        noTd.style.fontWeight = 'bold';
        noTd.style.backgroundColor = '#f8fafc'; // ใส่สีพื้นหลังให้อ่านง่าย
        tr.appendChild(noTd);

        // 2. ช่องแสดงชื่อพยาบาล
        const nameTd = document.createElement('td');
        nameTd.className = 'nurse-name';
        nameTd.innerText = nName;
        tr.appendChild(nameTd);

        // 3. วนลูปสร้างเซลล์วันที่ 1-31 พร้อมระบบไฟไฮไลต์
        for (let day = 1; day <= 31; day++) {
            const td = document.createElement('td');
            td.setAttribute('data-day', day); // แปะป้ายวันที่ไว้ใช้ทำไฟไฮไลต์แนวตั้ง

            const cellDiv = document.createElement('div');
            cellDiv.className = 'day-cell';
            cellDiv.id = `cell-${nId}-${day}`;
            
            const booking = currentBookings.find(b => parseInt(b[0]) === nId && parseInt(b[1]) === day);
            if (booking) {
                const rQueue = parseInt(booking[2]);
                cellDiv.classList.add(`queue${rQueue > 5 ? 5 : rQueue}`);
                cellDiv.innerHTML = `<span class="queue-label">R${rQueue}</span>`;
            }

            cellDiv.onclick = function() {
                handleCellClick(nId, day);
            };

            cellDiv.onclick = function() {
                handleCellClick(nId, day);
            };

            // 🟢 แก้ไขโค้ดระบบไฟ Hover เพื่อป้องกันปฏิทินหาย
            cellDiv.onmouseenter = function() {
                nameTd.style.backgroundColor = '#cbd5e1'; 
                nameTd.style.color = '#000000';
                
                // ค้นหาข้อความหัวตารางจากตัวเลขวันที่โดยตรง (ปลอดภัยกว่าการนับช่อง)
                const ths = document.getElementById('calendar-header-row').getElementsByTagName('th');
                for (let i = 0; i < ths.length; i++) {
                    if (ths[i].innerText == day) {
                        ths[i].classList.add('col-hover-header');
                        break;
                    }
                }
            };

            cellDiv.onmouseleave = function() {
                nameTd.style.backgroundColor = '#f8f9fa';
                nameTd.style.color = '';
                
                // ล้างค่าข้อความหัวตาราง
                const ths = document.getElementById('calendar-header-row').getElementsByTagName('th');
                for (let i = 0; i < ths.length; i++) {
                    if (ths[i].innerText == day) {
                        ths[i].classList.remove('col-hover-header');
                        break;
                    }
                }
            };


            // ⚠️ ห้ามลบ 2 บรรทัดนี้ (ปล่อยไว้ท้ายลูปเหมือนเดิม)
            td.appendChild(cellDiv);
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    });
}



function handleCellClick(nurseId, day) {
    
    // ล็อคให้จองของใครของมัน
    // if (activeNurseId !== null && activeNurseId !== nurseId) {
    //     showMessage('❌ กรุณาบันทึกหรือเคลียร์ข้อมูลของพยาบาลคนเดิมก่อนแก้ไขคนถัดไป', 'error');
    //     return;
    // }

    // 1. ตรวจสอบสถานะจริงจาก currentBookings
    const bookingIndex = currentBookings.findIndex(b => parseInt(b[0]) === nurseId && parseInt(b[1]) === day);
    const isBooked = bookingIndex !== -1;

    if (isBooked) {
        // กรณี: ยกเลิกการจอง
        const originalBooking = initialBookings.find(b => parseInt(b[0]) === nurseId && parseInt(b[1]) === day);
        addedChanges = addedChanges.filter(item => !(parseInt(item.nurse_id) === nurseId && parseInt(item.day) === day));
        
        if (originalBooking) {
            if (!deletedChanges.some(item => parseInt(item.nurse_id) === nurseId && parseInt(item.day) === day)) {
                deletedChanges.push({ nurse_id: nurseId, day: day });
            }
        }
        currentBookings.splice(bookingIndex, 1);
        } else {
        // กรณี: เพิ่มการจองใหม่
        const originalBooking = initialBookings.find(b => parseInt(b[0]) === nurseId && parseInt(b[1]) === day);
        deletedChanges = deletedChanges.filter(item => !(parseInt(item.nurse_id) === nurseId && parseInt(item.day) === day));
        
        if (!originalBooking) {
            if (!addedChanges.some(item => parseInt(item.nurse_id) === nurseId && parseInt(item.day) === day)) {
                addedChanges.push({ nurse_id: nurseId, day: day });
            }
        }
        
        // แก้ไขตรรกะตรงนี้: หาค่าคิว R ที่สูงที่สุดในวันนั้น แล้วบวก 1
        const dayBookings = currentBookings.filter(b => parseInt(b[1]) === day);
        let maxQueue = 0;
        dayBookings.forEach(b => {
            const q = parseInt(b[2]);
            if (q > maxQueue && q !== 999) maxQueue = q; // ไม่นับคิวจำลองเดิม
        });
        
        const tempQueue = maxQueue + 1; // คิวใหม่จะต่อท้ายคิวที่มากที่สุดเสมอ ไม่ซ้ำเลขเดิมแน่นอน
        
        currentBookings.push([nurseId, day, tempQueue]);
    }


    // 2. ตรวจสอบโควตา 5 วัน
    const totalNurseBookings = currentBookings.filter(b => parseInt(b[0]) === nurseId).length;
    if (totalNurseBookings > 5) {
        showMessage('❌ เลือกวันหยุดรวมเกินโควตา 5 วัน', 'error');
        handleCellClick(nurseId, day); // ดึงค่ากลับทันที
        return;
    }

    // 3. ควบคุมสถานะปุ่มบันทึก
    if (addedChanges.length === 0 && deletedChanges.length === 0) {
        activeNurseId = null;
        document.getElementById('btn-save').disabled = true;
    } else {
        activeNurseId = nurseId;
        document.getElementById('btn-save').disabled = false;
    }

    renderCalendar();
    updateStats();
}


function saveAllBookings() {
    const payload = { added: addedChanges, deleted: deletedChanges };

    fetch('/api/bookings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('❌ เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์', 'error');
    });
}


function updateStats() {
    document.getElementById('total-bookings').innerText = currentBookings.length;
    const uniqueNurses = new Set(currentBookings.map(b => b[0]));
    document.getElementById('unique-nurses').innerText = uniqueNurses.size;
}


function showMessage(text, type) {
    const msgDiv = document.getElementById('message');
    msgDiv.innerText = text;
    msgDiv.className = `message ${type}`;
    setTimeout(() => msgDiv.className = 'message', 4000);
}
