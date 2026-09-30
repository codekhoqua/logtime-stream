document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date_input');
    const today = new Date();
    dateInput.value = today.toISOString().split('T')[0];
    updateReportText();
    updateMetrics();
});

// ===== Time Utilities =====
function timeToMinutes(timeStr) {
    if (!timeStr) return 0;
    const parts = timeStr.split(':');
    if (parts.length === 3) {
        return parseInt(parts[0]) * 60 + parseInt(parts[1]) + Math.round(parseInt(parts[2]) / 60);
    } else if (parts.length === 2) {
        return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    }
    return parseInt(timeStr) || 0;
}

function formatMinutesToTime(totalMinutes) {
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    const s = 0;
    return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function formatTimeInput(input) {
    let val = input.value.replace(/[^0-9]/g, '');
    if (val.length > 2 && val.length <= 4) {
        val = val.slice(0, 2) + ':' + val.slice(2);
    } else if (val.length > 4) {
        val = val.slice(0, 2) + ':' + val.slice(2, 4) + ':' + val.slice(4, 6);
    }
    input.value = val;
}

// ===== Metrics =====
function updateMetrics() {
    const views = document.getElementById('live_viewer').value || '0';
    document.getElementById('metric_total_views').innerText = views;

    const rows = document.querySelectorAll('.stream-row');
    document.getElementById('metric_stream_count').innerText = rows.length;
}

// ===== Calculate =====
function calculateAll() {
    let totalMins = 0;
    const rows = document.querySelectorAll('.stream-row');

    rows.forEach((row) => {
        const timeStr = row.querySelector('.stream-time').value.trim();
        const mins = timeToMinutes(timeStr);

        const minInput = row.querySelector('.stream-minutes');
        if (mins > 0) {
            minInput.value = mins;
            totalMins += mins;
        } else {
            minInput.value = '';
        }
    });

    document.getElementById('total_minutes').value = totalMins;
    document.getElementById('metric_total_mins').innerText = totalMins;

    const timeFormatted = formatMinutesToTime(totalMins);
    document.getElementById('total_time').value = timeFormatted;
    document.getElementById('metric_total_time').innerText = timeFormatted;

    updateReportText();
    updateMetrics();
}

// ===== Stream Rows =====
let streamCount = 3;

function addStreamRow() {
    streamCount++;
    const container = document.getElementById('streams-container');
    const row = document.createElement('div');
    row.className = 'stream-row';
    row.id = 'stream-row-' + streamCount;

    row.innerHTML =
        '<div class="col-l">' +
        '<span class="row-label">Stream lần ' + streamCount + '</span>' +
        '<input type="hidden" class="time-mode-value" value="manual">' +
        '</div>' +
        '<div class="col-c">' +
        '<div class="mode-manual" id="mode-manual-' + streamCount + '" style="width: 100%;">' +
        '<input type="text" class="fancy-input stream-time" placeholder="HH:MM:SS" oninput="formatTimeInput(this)" onchange="calculateAll()" maxlength="8">' +
        '</div>' +
        '</div>' +
        '<div class="col-r">' +
        '<input type="number" class="fancy-input stream-minutes table-input-readonly" readonly>' +
        '</div>' +
        '<div class="col-x">' +
        '<button class="btn-remove" onclick="removeStreamRow(\'' + row.id + '\')" title="Xóa dòng này">✕</button>' +
        '</div>';

    container.appendChild(row);
    updateMetrics();
}

function removeStreamRow(id) {
    const row = document.getElementById(id);
    if (row) {
        row.remove();
        calculateAll();
        updateMetrics();
    }
}

// ===== Report =====
function updateReportText() {
    const dateStr = document.getElementById('date_input').value;
    let dateFormatted = '...';
    if (dateStr) {
        const d = new Date(dateStr);
        dateFormatted = d.getDate() + ' tháng ' + (d.getMonth() + 1) + ' năm ' + d.getFullYear();
    }

    const idVal = document.getElementById('id_input').value || '...';
    const platformName = document.getElementById('platform_name').value;
    const views = document.getElementById('live_viewer').value || '0';
    const totalTime = document.getElementById('total_time').value || '00:00:00';
    const totalMins = document.getElementById('total_minutes').value || '0';

    document.getElementById('rp_line1').innerText = '*Em gửi Thời lượng Live - Ngày ' + dateFormatted + '*';
    document.getElementById('rp_line2').innerText = 'Thời gian: ' + totalTime + ' tương đương ' + totalMins + ' phút';
    document.getElementById('rp_line3').innerText = 'ID: ' + idVal + ' - ' + platformName;
    document.getElementById('rp_line4').innerText = 'Tổng số View: ' + views;
}

// ===== Copy Report =====
async function copyReport() {
    const reportText = [
        document.getElementById('rp_line1').innerText,
        document.getElementById('rp_line2').innerText,
        document.getElementById('rp_line3').innerText,
        document.getElementById('rp_line4').innerText,
    ].join('\n');

    try {
        await navigator.clipboard.writeText(reportText);
        Swal.fire({
            icon: 'success',
            title: 'Thành công!',
            text: 'Đã copy mẫu báo cáo vào Clipboard.',
            timer: 1500,
            showConfirmButton: false
        });
    } catch (err) {
        console.error('Failed to copy text: ', err);
        Swal.fire({
            icon: 'error',
            title: 'Lỗi',
            text: 'Không thể copy mẫu báo cáo.'
        });
    }
}

// ===== Submit Data =====
function submitData(forceSubmit = false) {
    // Validations
    const dateStr = document.getElementById('date_input').value;
    if (!dateStr) {
        Swal.fire('Thiếu thông tin', 'Vui lòng chọn Ngày báo cáo!', 'warning');
        return;
    }

    const views = document.getElementById('live_viewer').value;
    if (views === '') {
        Swal.fire('Thiếu thông tin', 'Vui lòng nhập Tổng live viewer!', 'warning');
        return;
    }

    const totalMins = document.getElementById('total_minutes').value;
    if (parseInt(totalMins) <= 0) {
        Swal.fire('Thiếu thông tin', 'Bạn chưa nhập Thời lượng stream hợp lệ (tổng phút phải > 0)!', 'warning');
        return;
    }

    let hasInvalidRange = false;
    const rows = document.querySelectorAll('.stream-row');
    rows.forEach((row) => {
        const modeVal = row.querySelector('.time-mode-value');
        const mode = modeVal ? modeVal.value : 'manual';
        if (mode === 'range') {
            const startStr = row.querySelector('.stream-start').value;
            const endStr = row.querySelector('.stream-end').value;
            if (startStr && endStr) {
                if (new Date(endStr) < new Date(startStr)) {
                    hasInvalidRange = true;
                }
            }
        }
    });

    if (hasInvalidRange) {
        Swal.fire('Lỗi thông tin', 'Có khung giờ kết thúc nhỏ hơn bắt đầu. Vui lòng kiểm tra lại!', 'error');
        return;
    }

    Swal.fire({
        title: 'Đang đẩy dữ liệu...',

        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    const payload = {
        hash: document.getElementById('hash_input').value,
        uid: document.getElementById('id_input').value,
        date: document.getElementById('date_input').value,
        time: document.getElementById('total_time').value,
        minutes: document.getElementById('total_minutes').value,
        live_viewer: document.getElementById('live_viewer').value,
        note: '',
        force: forceSubmit
    };

    fetch('/submit_log', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.already_logged) {
                Swal.fire({
                    title: 'Đã báo cáo hôm nay',
                    text: data.message,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Có, báo cáo thêm',
                    cancelButtonText: 'Hủy bỏ'
                }).then((result) => {
                    if (result.isConfirmed) {
                        submitData(true);
                    }
                });
            } else if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Lưu thành công!',
                    text: data.message || 'Đã lưu thành công vào Google Sheets!',
                    timer: 2000,
                    showConfirmButton: false
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Lỗi',
                    text: data.message
                });
            }
        })
        .catch(error => {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi máy chủ',
                text: error.toString()
            });
        });
}
