#  Parking Management System — Automated Testing

A fully client-side, single-file web application for managing parking slots, paired with a complete Selenium automated test suite.

Built with vanilla HTML, CSS, and JavaScript — no server or build step required.

![Tests](https://github.com/riteshs-direct/parking-management-system-automated-testing/actions/workflows/tests.yml/badge.svg)

---

## Features

| Module | Description |
|---|---|
| Authentication | Login / Register with role-based access (Admin & Employee) |
| Dashboard | Live stats: total, available, and occupied slots |
| Slot Monitor | Visual grid of all 30 slots with type and status filters |
| Allocate / De-allocate | Assign vehicles to slots and mark exits |
| Vehicle Registry | Register vehicles with owner details; search and filter |
| Reports | Date-range filtered allocation log; role-scoped |
| Notifications | System event feed with info, warning, and danger alerts |
| User Management | Admin-only: revoke access, promote/demote roles |
| Backup & Restore | Export full data as JSON; restore from file |

---

## Project Structure

```
parking-management-system-automated-testing/
├── .github/
│   └── workflows/
│       └── tests.yml
├── parking_System.html
├── test_parking_system.py
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## Quick Start

Open `parking_System.html` directly in any modern browser — no install needed.

**Default credentials:** `admin` / `admin123`

---

## Running the Tests

### Prerequisites
- Python 3.8+
- Google Chrome
- ChromeDriver matching your Chrome version → https://googlechromelabs.github.io/chrome-for-testing/
- Place `chromedriver.exe` in the project root

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run all tests
```bash
python -m pytest test_parking_system.py -v
```

### Generate HTML report
```bash
python -m pytest test_parking_system.py -v --html=report.html --self-contained-html
```

---

## Test Coverage

| Class | Description | Tests |
|---|---|---|
| TC01 | Auth screen rendering | 6 |
| TC02 | Login functionality | 7 |
| TC03 | Registration | 5 |
| TC04 | Dashboard | 5 |
| TC05 | Slot Monitor | 8 |
| TC06 | Slot Allocation | 7 |
| TC07 | Vehicle Registry | 7 |
| TC08 | Reports | 6 |
| TC09 | Notifications | 4 |
| TC10 | User Management | 5 |
| TC11 | Logout | 3 |
| TC12 | Navigation | 8 |

---

## Tech Stack

- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (ES6+)
- **Storage:** localStorage (no backend)
- **Testing:** Python unittest + Selenium WebDriver + pytest

---

## License

MIT
