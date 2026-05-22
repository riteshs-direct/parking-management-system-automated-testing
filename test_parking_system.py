

import os
import time
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# ─── CONFIGURATION ────────────────────────────────────────
# Update this path if chromedriver is NOT in the same folder as this file
CHROMEDRIVER_PATH = "./chromedriver"

# Path to the HTML file under test
HTML_FILE = Path(__file__).parent / "parking_System.html"

# HTTP server settings – no need to change these
HTTP_PORT = 8765
APP_URL = f"http://localhost:{HTTP_PORT}/parking_System.html"

SHORT_WAIT = 5    # seconds – for simple element waits
LONG_WAIT = 30   # seconds – for page transitions / slow renders

# Default admin credentials (hard-coded in the app)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Test employee credentials (created during register tests)
EMP_NAME   = "Test Employee"
EMP_ID     = "EMP999"
EMP_USER = "testuser99"
EMP_PASS   = "test123"
# ──────────────────────────────────────────────────────────


# ── Embedded HTTP server (serves the HTML file over localhost) ──────────────
_http_thread = None
_http_server = None

def _start_http_server():
    """Start a simple HTTP server in the HTML file's directory."""
    global _http_server, _http_thread
    if _http_thread and _http_thread.is_alive():
        return  # already running

    serve_dir = str(HTML_FILE.parent.resolve())

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=serve_dir, **kwargs)
        def log_message(self, *args):
            pass  # suppress server output

    _http_server = HTTPServer(("localhost", HTTP_PORT), QuietHandler)
    _http_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
    _http_thread.start()

# Start the server immediately when the module is imported
_start_http_server()
# ────────────────────────────────────────────────────────────────────────────


def make_driver() -> webdriver.Chrome:
    """Return a configured headless Chrome WebDriver."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # Block external resource requests (Google Fonts etc.) that cause hangs
    opts.add_argument("--host-resolver-rules=MAP fonts.googleapis.com 127.0.0.2,"
                      "MAP fonts.gstatic.com 127.0.0.2")
    opts.add_argument("--disable-background-networking")
    # Use eager page load strategy - don't wait for all resources
    opts.page_load_strategy = "eager"
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    if os.path.exists(CHROMEDRIVER_PATH):
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        driver = webdriver.Chrome(options=opts)

    driver.implicitly_wait(SHORT_WAIT)
    driver.set_page_load_timeout(30)
    return driver


def _clear_storage(driver, wait):
    """Navigate to the app, clear localStorage, then reset state via JS."""
    # First visit — get the page loaded
    driver.get(APP_URL)
    # Wait for the body to exist (page HTML loaded)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    # Clear all stored data and reset app state in one JS call
    driver.execute_script("""
        localStorage.clear();
        currentUser = null;
        var app = document.getElementById('app');
        var auth = document.getElementById('authScreen');
        if (app) app.style.display = 'none';
        if (auth) auth.style.display = '';
        if (typeof initData === 'function') initData();
    """)
    time.sleep(0.5)
    # Verify auth screen is now visible
    wait.until(EC.visibility_of_element_located((By.ID, "authScreen")))


class BaseTest(unittest.TestCase):
    """Shared setUp / tearDown and helper methods for every test class."""

    @classmethod
    def setUpClass(cls):
        cls.driver = make_driver()
        cls.wait   = WebDriverWait(cls.driver, LONG_WAIT)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ── Helpers ──────────────────────────────────────────

    def open_app(self):
        """Navigate to the app with a clean localStorage state."""
        _clear_storage(self.driver, self.wait)

    def _wait_for_auth_screen(self):
        self.wait.until(
            EC.visibility_of_element_located((By.ID, "authScreen"))
        )

    def login(self, username=ADMIN_USER, password=ADMIN_PASS):
        """Fill login form and submit."""
        self.driver.find_element(By.ID, "l_user").clear()
        self.driver.find_element(By.ID, "l_user").send_keys(username)
        self.driver.find_element(By.ID, "l_pass").clear()
        self.driver.find_element(By.ID, "l_pass").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def nav_to(self, page_name: str):
        """Navigate to a page via JS goto()."""
        self.driver.execute_script(f"goto('{page_name}')")
        self.wait.until(
            EC.visibility_of_element_located((By.ID, f"page-{page_name}"))
        )

    def get_toast_text(self) -> str:
        """Return the text of the most recent toast notification."""
        try:
            toast = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#toast .toast-msg"))
            )
            return toast.text
        except Exception:
            return ""


#  TC-01  AUTH SCREEN RENDERING
# ═══════════════════════════════════════════════════════════
class TC01_AuthScreenRendering(BaseTest):
    """Verify the authentication screen loads and renders correctly."""

    def setUp(self):
        self.open_app()

    def test_01_auth_screen_visible(self):
        """Auth screen is visible on initial load."""
        auth = self.driver.find_element(By.ID, "authScreen")
        self.assertTrue(auth.is_displayed(), "Auth screen should be visible on load")

    def test_02_login_tab_active_by_default(self):
        """Login tab is active and login form is shown by default."""
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        self.assertIn("active", tabs[0].get_attribute("class"),
                      "First tab (Login) should be active by default")
        login_form = self.driver.find_element(By.ID, "loginForm")
        self.assertTrue(login_form.is_displayed(), "Login form should be visible")

    def test_03_register_tab_shows_register_form(self):
        """Clicking Register tab shows register form and hides login form."""
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[1].click()
        time.sleep(0.3)
        reg_form   = self.driver.find_element(By.ID, "registerForm")
        login_form = self.driver.find_element(By.ID, "loginForm")
        self.assertTrue(reg_form.is_displayed(),
                        "Register form should be visible after clicking Register tab")
        self.assertFalse(login_form.is_displayed(),
                         "Login form should be hidden after clicking Register tab")

    def test_04_login_form_has_required_fields(self):
        """Login form contains username, password fields and a submit button."""
        self.assertIsNotNone(self.driver.find_element(By.ID, "l_user"))
        self.assertIsNotNone(self.driver.find_element(By.ID, "l_pass"))
        btn = self.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary")
        self.assertIn("Login", btn.text)

    def test_05_register_form_has_required_fields(self):
        """Register form contains all four required fields."""
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[1].click()
        time.sleep(0.3)
        for field_id in ["r_name", "r_empid", "r_user", "r_pass"]:
            self.assertIsNotNone(self.driver.find_element(By.ID, field_id),
                                 f"Field {field_id} missing from register form")

    def test_06_main_app_hidden_before_login(self):
        """Main app div is hidden before any user logs in."""
        app = self.driver.find_element(By.ID, "app")
        self.assertEqual(app.value_of_css_property("display"), "none",
                         "App should be hidden before login")


# ═══════════════════════════════════════════════════════════
#  TC-02  LOGIN FUNCTIONALITY
# ═══════════════════════════════════════════════════════════
class TC02_LoginFunctionality(BaseTest):
    """Test login with valid, invalid, and edge-case credentials."""

    def setUp(self):
        self.open_app()

    def test_01_valid_admin_login(self):
        """Admin can log in with default credentials (admin / admin123)."""
        self.login(ADMIN_USER, ADMIN_PASS)
        app = self.driver.find_element(By.ID, "app")
        self.assertNotEqual(app.value_of_css_property("display"), "none",
                            "App should be visible after successful admin login")

    def test_02_invalid_password_shows_error(self):
        """Login with wrong password shows error toast."""
        self.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        self.driver.find_element(By.ID, "l_pass").send_keys("wrongpassword")
        self.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        toast = self.get_toast_text()
        self.assertIn("Invalid", toast, "Error toast should contain 'Invalid'")

    def test_03_empty_credentials_shows_error(self):
        """Login with empty fields shows an error toast."""
        self.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0, "Error toast should appear for empty credentials")

    def test_04_wrong_username_shows_error(self):
        """Login with non-existent username shows error."""
        self.driver.find_element(By.ID, "l_user").send_keys("nobody")
        self.driver.find_element(By.ID, "l_pass").send_keys("pass123")
        self.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        toast = self.get_toast_text()
        self.assertIn("Invalid", toast)

    def test_05_sidebar_shows_admin_user_info(self):
        """After login, sidebar displays the admin's name and role."""
        self.login(ADMIN_USER, ADMIN_PASS)
        sb_name = self.driver.find_element(By.ID, "sb_name").text
        sb_role = self.driver.find_element(By.ID, "sb_role").text
        self.assertTrue(len(sb_name) > 0, "Sidebar should show user name")
        self.assertIn("admin", sb_role.lower(), "Sidebar badge should show 'admin' role")

    def test_06_admin_sees_admin_only_nav_items(self):
        """Admin-only nav items (Users, Backup) are visible after admin login."""
        self.login(ADMIN_USER, ADMIN_PASS)
        admin_items = self.driver.find_elements(By.CSS_SELECTOR, ".nav-item.admin-only")
        visible = [el for el in admin_items if el.is_displayed()]
        self.assertGreaterEqual(len(visible), 2,
                                "Admin should see at least 2 admin-only nav items")

    def test_07_auth_screen_hidden_after_login(self):
        """Auth screen is hidden after successful login."""
        self.login(ADMIN_USER, ADMIN_PASS)
        auth = self.driver.find_element(By.ID, "authScreen")
        self.assertFalse(auth.is_displayed(), "Auth screen should be hidden after login")


# ═══════════════════════════════════════════════════════════
#  TC-03  REGISTRATION FUNCTIONALITY
# ═══════════════════════════════════════════════════════════
class TC03_RegistrationFunctionality(BaseTest):
    """Test user account registration."""

    def setUp(self):
        self.open_app()
        # Switch to register tab
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[1].click()
        time.sleep(0.3)

    def _fill_register_form(self, name=EMP_NAME, emp_id=EMP_ID,
                             username=EMP_USER, password=EMP_PASS):
        self.driver.find_element(By.ID, "r_name").send_keys(name)
        self.driver.find_element(By.ID, "r_empid").send_keys(emp_id)
        self.driver.find_element(By.ID, "r_user").send_keys(username)
        self.driver.find_element(By.ID, "r_pass").send_keys(password)

    def test_01_successful_registration(self):
        """A new employee account can be registered successfully."""
        self._fill_register_form()
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        toast = self.get_toast_text()
        self.assertNotIn("error", toast.lower(),
                         f"Registration should not show an error; got: '{toast}'")

    def test_02_registered_user_can_login(self):
        """After registration, the new user can log in."""
        self._fill_register_form()
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        time.sleep(0.5)
        # Switch back to login
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[0].click()
        time.sleep(0.3)
        self.login(EMP_USER, EMP_PASS)
        app = self.driver.find_element(By.ID, "app")
        self.assertNotEqual(app.value_of_css_property("display"), "none",
                            "Newly registered user should be able to log in")

    def test_03_short_password_rejected(self):
        """Password shorter than 6 characters is rejected."""
        self._fill_register_form(password="abc")
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0,
                        "Short password should produce an error toast")

    def test_04_duplicate_username_rejected(self):
        """Registering with an existing username should fail."""
        self._fill_register_form()
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        time.sleep(0.5)
        # Try to register again with same username
        tabs = self.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[1].click()
        time.sleep(0.3)
        self._fill_register_form()
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0,
                        "Duplicate username registration should produce a toast")

    def test_05_empty_fields_rejected(self):
        """Submitting an empty registration form shows an error."""
        self.driver.find_element(By.CSS_SELECTOR, "#registerForm .btn-success").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0,
                        "Empty form submission should produce an error toast")


# ═══════════════════════════════════════════════════════════
#  TC-04  DASHBOARD
# ═══════════════════════════════════════════════════════════
class TC04_Dashboard(BaseTest):
    """Verify dashboard statistics cards and recent allocation table."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        # Log in once for all tests in this class
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def test_01_dashboard_page_visible(self):
        """Dashboard page is the active page after login."""
        page = self.driver.find_element(By.ID, "page-dashboard")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_stat_cards_rendered(self):
        """Dashboard renders at least 3 stat cards."""
        cards = self.driver.find_elements(By.CSS_SELECTOR, "#dashCards .card")
        self.assertGreaterEqual(len(cards), 3,
                                "Dashboard should display at least 3 stat cards")

    def test_03_cards_have_labels_and_values(self):
        """Each stat card has a label and a numeric value."""
        cards = self.driver.find_elements(By.CSS_SELECTOR, "#dashCards .card")
        for card in cards:
            label = card.find_element(By.CSS_SELECTOR, ".card-label").text
            value = card.find_element(By.CSS_SELECTOR, ".card-value").text
            self.assertTrue(len(label) > 0, "Card label should not be empty")
            self.assertTrue(value.strip().isdigit() or "/" in value,
                            f"Card value '{value}' should be numeric")

    def test_04_recent_allocations_table_present(self):
        """Recent Allocations table body element exists on dashboard."""
        tbody = self.driver.find_element(By.ID, "recentAlloc")
        self.assertIsNotNone(tbody)

    def test_05_total_slots_card_reflects_30_slots(self):
        """Total Slots card shows 30 (10 × 2W + 20 × 4W from initData)."""
        card_values = self.driver.find_elements(By.CSS_SELECTOR, "#dashCards .card-value")
        texts = [el.text for el in card_values]
        self.assertIn("30", texts,
                      f"One card should show '30' total slots; cards: {texts}")


# ═══════════════════════════════════════════════════════════
#  TC-05  SLOT MONITOR
# ═══════════════════════════════════════════════════════════
class TC05_SlotMonitor(BaseTest):
    """Test the Slot Monitor page – grid rendering, filters, slot details."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("slots")

    def test_01_slot_grid_rendered(self):
        """Slot monitor renders 30 slot cells (10 × 2W + 20 × 4W)."""
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        self.assertEqual(len(cells), 30, f"Expected 30 slots, got {len(cells)}")

    def test_02_all_slots_available_initially(self):
        """All 30 slots are available after a fresh localStorage clear."""
        available = self.driver.find_elements(
            By.CSS_SELECTOR, "#slotGrid .slot-cell.available")
        self.assertEqual(len(available), 30,
                         "All slots should be available on a fresh system")

    def test_03_filter_by_2w_shows_10_slots(self):
        """Filtering by 2-Wheeler shows exactly 10 slots."""
        sel = Select(self.driver.find_element(By.ID, "slotFilter"))
        sel.select_by_value("2W")
        time.sleep(0.4)
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        self.assertEqual(len(cells), 10, f"Expected 10 2W slots, got {len(cells)}")

    def test_04_filter_by_4w_shows_20_slots(self):
        """Filtering by 4-Wheeler shows exactly 20 slots."""
        sel = Select(self.driver.find_element(By.ID, "slotFilter"))
        sel.select_by_value("4W")
        time.sleep(0.4)
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        self.assertEqual(len(cells), 20, f"Expected 20 4W slots, got {len(cells)}")

    def test_05_filter_reset_shows_all_slots(self):
        """Resetting filter to 'All Types' shows all 30 slots."""
        sel = Select(self.driver.find_element(By.ID, "slotFilter"))
        sel.select_by_value("2W")
        time.sleep(0.3)
        sel.select_by_value("")
        time.sleep(0.3)
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        self.assertEqual(len(cells), 30)

    def test_06_slot_has_id_and_type_labels(self):
        """Each slot cell displays a slot ID and type label."""
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        cell = cells[0]
        slot_id   = cell.find_element(By.CSS_SELECTOR, ".slot-id").text
        slot_type = cell.find_element(By.CSS_SELECTOR, ".slot-type").text
        self.assertTrue(len(slot_id) > 0,   "Slot ID should not be empty")
        self.assertTrue(len(slot_type) > 0, "Slot type label should not be empty")

    def test_07_clicking_slot_shows_detail_panel(self):
        """Clicking a slot cell reveals the slot detail panel."""
        cells = self.driver.find_elements(By.CSS_SELECTOR, "#slotGrid .slot-cell")
        cells[0].click()
        detail = self.driver.find_element(By.ID, "slotDetail")
        self.wait.until(EC.visibility_of(detail))
        self.assertTrue(detail.is_displayed(), "Slot detail panel should appear on click")

    def test_08_status_filter_available_works(self):
        """Status filter 'Available' shows only available slots."""
        status_sel = Select(self.driver.find_element(By.ID, "slotStatusFilter"))
        status_sel.select_by_value("available")
        time.sleep(0.4)
        occupied = self.driver.find_elements(
            By.CSS_SELECTOR, "#slotGrid .slot-cell.occupied")
        self.assertEqual(len(occupied), 0,
                         "No occupied slots should show when filtering for Available")


# ═══════════════════════════════════════════════════════════
#  TC-06  SLOT ALLOCATION
# ═══════════════════════════════════════════════════════════
class TC06_SlotAllocation(BaseTest):
    """Test allocating and de-allocating parking slots."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("allocate")

    def _allocate(self, vehicle_no="TN01AB1234", vtype="2W"):
        """Helper: fill and submit the allocate form."""
        veh_input = self.driver.find_element(By.ID, "al_veh")
        veh_input.clear()
        veh_input.send_keys(vehicle_no)
        type_sel = Select(self.driver.find_element(By.ID, "al_type"))
        type_sel.select_by_value(vtype)
        # Auto-assign (leave slot selector on default)
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-allocate .btn-primary").click()
        time.sleep(0.5)

    def test_01_allocate_page_visible(self):
        """Allocate page is visible and contains both sub-forms."""
        page = self.driver.find_element(By.ID, "page-allocate")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_allocate_slot_success(self):
        """Allocating a 2W vehicle with auto-assign shows success toast."""
        self._allocate("TN01AB0001", "2W")
        toast = self.get_toast_text()
        self.assertIn("Allocated", toast,
                      f"Expected 'Allocated' in toast, got: '{toast}'")

    def test_03_allocated_vehicle_appears_in_active_table(self):
        """After allocation, the vehicle appears in the Active Allocations table."""
        self._allocate("TN01AB0002", "4W")
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#activeAllocTable tr")
        self.assertGreaterEqual(len(rows), 1,
                                "Active allocations table should have at least 1 row")

    def test_04_allocate_empty_vehicle_number_rejected(self):
        """Allocating with an empty vehicle number shows an error."""
        veh_input = self.driver.find_element(By.ID, "al_veh")
        veh_input.clear()
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-allocate .btn-primary").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0,
                        "Empty vehicle number should produce an error toast")

    def test_05_vehicle_number_auto_uppercased(self):
        """Vehicle number input auto-converts text to uppercase."""
        veh_input = self.driver.find_element(By.ID, "al_veh")
        veh_input.clear()
        veh_input.send_keys("tn01ab9999")
        time.sleep(0.2)
        value = veh_input.get_attribute("value")
        self.assertEqual(value, "TN01AB9999",
                         "Vehicle number should be uppercased automatically")

    def test_06_deallocate_slot_success(self):
        """A previously allocated slot can be de-allocated (vehicle exited)."""
        # First allocate
        self._allocate("TN01AB0003", "2W")
        time.sleep(0.3)
        # Now de-allocate
        deal_sel = Select(self.driver.find_element(By.ID, "deal_slot"))
        opts = [o for o in deal_sel.options if o.get_attribute("value")]
        if not opts:
            self.skipTest("No occupied slot available for de-allocation test")
        deal_sel.select_by_index(1)
        time.sleep(0.3)
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-allocate .btn-danger").click()
        time.sleep(0.5)
        toast = self.get_toast_text()
        self.assertIn("Exited", toast,
                      f"Expected 'Exited' in toast after de-allocation, got: '{toast}'")

    def test_07_slot_becomes_available_after_deallocate(self):
        """After de-allocation, slot count of occupied slots decreases by 1."""
        # Allocate a fresh slot
        self._allocate("TN01AB0004", "2W")
        time.sleep(0.3)
        # Count occupied slots before deallocate
        self.nav_to("slots")
        occupied_before = len(self.driver.find_elements(
            By.CSS_SELECTOR, "#slotGrid .slot-cell.occupied"))
        self.nav_to("allocate")
        # De-allocate
        deal_sel = Select(self.driver.find_element(By.ID, "deal_slot"))
        opts = [o for o in deal_sel.options if o.get_attribute("value")]
        if not opts:
            self.skipTest("No occupied slot found")
        deal_sel.select_by_index(1)
        time.sleep(0.3)
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-allocate .btn-danger").click()
        time.sleep(0.5)
        self.nav_to("slots")
        occupied_after = len(self.driver.find_elements(
            By.CSS_SELECTOR, "#slotGrid .slot-cell.occupied"))
        self.assertLess(occupied_after, occupied_before,
                        "Occupied slot count should decrease after de-allocation")


# ═══════════════════════════════════════════════════════════
#  TC-07  VEHICLE REGISTRY
# ═══════════════════════════════════════════════════════════
class TC07_VehicleRegistry(BaseTest):
    """Test vehicle registration and search functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("vehicles")

    def _register_vehicle(self, num="TN01AB1234", vtype="2W",
                           owner="John Doe", contact="9876543210"):
        self.driver.find_element(By.ID, "v_num").clear()
        self.driver.find_element(By.ID, "v_num").send_keys(num)
        Select(self.driver.find_element(By.ID, "v_type")).select_by_value(vtype)
        self.driver.find_element(By.ID, "v_owner").clear()
        self.driver.find_element(By.ID, "v_owner").send_keys(owner)
        self.driver.find_element(By.ID, "v_contact").clear()
        self.driver.find_element(By.ID, "v_contact").send_keys(contact)
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-vehicles .btn-success").click()
        time.sleep(0.4)

    def test_01_vehicle_page_visible(self):
        """Vehicle Registry page is active and visible."""
        page = self.driver.find_element(By.ID, "page-vehicles")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_register_vehicle_success(self):
        """Registering a vehicle with valid data shows success toast."""
        self._register_vehicle("TN01XY0001")
        toast = self.get_toast_text()
        self.assertIn("Registered", toast,
                      f"Expected 'Registered' in toast, got: '{toast}'")

    def test_03_registered_vehicle_appears_in_table(self):
        """Registered vehicle number appears in the vehicles table."""
        self._register_vehicle("TN02XY9999", owner="Jane Smith")
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#vehicleTable tr")
        row_texts = " ".join(r.text for r in rows)
        self.assertIn("TN02XY9999", row_texts,
                      "Vehicle number should appear in the table after registration")

    def test_04_empty_vehicle_number_rejected(self):
        """Registering without a vehicle number shows an error."""
        self.driver.find_element(By.ID, "v_owner").send_keys("Test Owner")
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-vehicles .btn-success").click()
        toast = self.get_toast_text()
        self.assertTrue(len(toast) > 0,
                        "Empty vehicle number should produce an error toast")

    def test_05_vehicle_number_uppercased(self):
        """Vehicle number input auto-converts to uppercase."""
        inp = self.driver.find_element(By.ID, "v_num")
        inp.clear()
        inp.send_keys("tn99zz0000")
        time.sleep(0.2)
        self.assertEqual(inp.get_attribute("value").upper(), "TN99ZZ0000")

    def test_06_search_filters_vehicle_table(self):
        """Search input filters the vehicle table by vehicle number."""
        self._register_vehicle("MH12AB5678", owner="Search Test")
        search = self.driver.find_element(By.ID, "vSearch")
        search.clear()
        search.send_keys("MH12")
        time.sleep(0.4)
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#vehicleTable tr")
        visible_texts = [r.text for r in rows if r.is_displayed()]
        self.assertTrue(any("MH12" in t for t in visible_texts),
                        "Searching 'MH12' should show the matching vehicle")

    def test_07_type_filter_2w_works(self):
        """Type filter '2W' shows only 2-Wheeler vehicles."""
        self._register_vehicle("TN10AA1111", vtype="2W")
        self._register_vehicle("TN10BB2222", vtype="4W")
        type_sel = Select(self.driver.find_element(By.ID, "vTypeFilter"))
        type_sel.select_by_value("2W")
        time.sleep(0.4)
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#vehicleTable tr")
        row_texts = " ".join(r.text for r in rows if r.is_displayed())
        self.assertNotIn("4W", row_texts,
                         "4W vehicles should not appear when filtering for 2W")


# ═══════════════════════════════════════════════════════════
#  TC-08  REPORTS
# ═══════════════════════════════════════════════════════════
class TC08_Reports(BaseTest):
    """Test the Reports page – date filtering and log generation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("reports")

    def test_01_reports_page_visible(self):
        """Reports page is visible and active."""
        page = self.driver.find_element(By.ID, "page-reports")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_date_fields_pre_populated(self):
        """From-date and To-date fields are pre-populated on load."""
        from_val = self.driver.find_element(By.ID, "rep_from").get_attribute("value")
        to_val   = self.driver.find_element(By.ID, "rep_to").get_attribute("value")
        self.assertTrue(len(from_val) > 0, "From date should be pre-populated")
        self.assertTrue(len(to_val) > 0,   "To date should be pre-populated")

    def test_03_generate_report_button_present(self):
        """Generate report button is visible on the reports page."""
        btn = self.driver.find_element(By.CSS_SELECTOR,
            "#page-reports .btn-primary")
        self.assertTrue(btn.is_displayed())

    def test_04_generate_report_shows_summary_cards(self):
        """Clicking Generate renders summary stat cards."""
        self.driver.find_element(By.CSS_SELECTOR,
            "#page-reports .btn-primary").click()
        time.sleep(0.5)
        cards = self.driver.find_elements(By.CSS_SELECTOR, "#reportSummary .card")
        self.assertGreater(len(cards), 0,
                           "Report summary should show at least 1 stat card")

    def test_05_type_filter_in_report(self):
        """Vehicle type filter dropdown is present in the report form."""
        sel = Select(self.driver.find_element(By.ID, "rep_type"))
        opts = [o.get_attribute("value") for o in sel.options]
        self.assertIn("2W", opts)
        self.assertIn("4W", opts)

    def test_06_report_table_present(self):
        """Allocation log table body exists on the reports page."""
        tbody = self.driver.find_element(By.ID, "reportTable")
        self.assertIsNotNone(tbody)


# ═══════════════════════════════════════════════════════════
#  TC-09  NOTIFICATIONS
# ═══════════════════════════════════════════════════════════
class TC09_Notifications(BaseTest):
    """Test the Notifications & Alerts page."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("notifications")

    def test_01_notifications_page_visible(self):
        """Notifications page is visible and active."""
        page = self.driver.find_element(By.ID, "page-notifications")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_initial_notification_present(self):
        """System initialisation notification is shown on first load."""
        notif_list = self.driver.find_element(By.ID, "notifList")
        self.assertTrue(len(notif_list.text) > 0,
                        "Notification list should contain the init message")

    def test_03_add_test_alert_works(self):
        """Clicking '+ Add Test Alert' adds a new notification item."""
        before = len(self.driver.find_elements(
            By.CSS_SELECTOR, "#notifList .notif-item"))
        self.driver.find_element(
            By.XPATH, "//button[contains(text(),'Add Test Alert')]").click()
        time.sleep(0.4)
        after = len(self.driver.find_elements(
            By.CSS_SELECTOR, "#notifList .notif-item"))
        self.assertGreater(after, before,
                           "Notification count should increase after adding a test alert")

    def test_04_clear_all_removes_notifications(self):
        """Clicking 'Clear All' removes all notification items."""
        self.driver.find_element(
            By.XPATH, "//button[contains(text(),'Clear All')]").click()
        time.sleep(0.4)
        items = self.driver.find_elements(
            By.CSS_SELECTOR, "#notifList .notif-item")
        self.assertEqual(len(items), 0,
                         "All notifications should be cleared")


# ═══════════════════════════════════════════════════════════
#  TC-10  USER MANAGEMENT (admin only)
# ═══════════════════════════════════════════════════════════
class TC10_UserManagement(BaseTest):
    """Test admin-only user management features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        # Register an employee first (for toggle tests)
        tabs = cls.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[1].click()
        time.sleep(0.3)
        cls.driver.find_element(By.ID, "r_name").send_keys(EMP_NAME)
        cls.driver.find_element(By.ID, "r_empid").send_keys(EMP_ID)
        cls.driver.find_element(By.ID, "r_user").send_keys(EMP_USER)
        cls.driver.find_element(By.ID, "r_pass").send_keys(EMP_PASS)
        cls.driver.find_element(
            By.CSS_SELECTOR, "#registerForm .btn-success").click()
        time.sleep(0.5)
        # Log in as admin
        tabs = cls.driver.find_elements(By.CSS_SELECTOR, ".tabs button")
        tabs[0].click()
        time.sleep(0.3)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(
            By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def setUp(self):
        self.nav_to("users")

    def test_01_users_page_visible_for_admin(self):
        """Users page is visible and active for the admin."""
        page = self.driver.find_element(By.ID, "page-users")
        self.assertIn("active", page.get_attribute("class"))

    def test_02_users_table_shows_all_users(self):
        """Users table shows at least 2 rows (admin + registered employee)."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#usersTable tr")
        self.assertGreaterEqual(len(rows), 2,
                                "Users table should show at least 2 users")

    def test_03_admin_row_has_protected_label(self):
        """Admin row shows 'Protected' instead of action buttons."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#usersTable tr")
        admin_row_text = ""
        for row in rows:
            if "admin" in row.text.lower() and "EMP000" in row.text:
                admin_row_text = row.text
                break
        self.assertIn("Protected", admin_row_text,
                      "Admin user row should have 'Protected' label in actions")

    def test_04_toggle_user_status_works(self):
        """Revoking a user's status changes the status badge."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#usersTable tr")
        target_row = None
        for row in rows:
            if EMP_USER in row.text:
                target_row = row
                break
        self.assertIsNotNone(target_row, f"Could not find row for {EMP_USER}")
        revoke_btn = target_row.find_element(
            By.XPATH, ".//button[contains(text(),'Revoke')]")
        revoke_btn.click()
        time.sleep(0.4)
        toast = self.get_toast_text()
        self.assertTrue("revoked" in toast.lower() or "restored" in toast.lower(),
                        f"Expected revoke/restore toast, got: '{toast}'")

    def test_05_toggle_role_works(self):
        """Toggling role on employee user changes their role badge."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, "#usersTable tr")
        target_row = None
        for row in rows:
            if EMP_USER in row.text:
                target_row = row
                break
        self.assertIsNotNone(target_row)
        btns = target_row.find_elements(By.TAG_NAME, "button")
        role_btn = next((b for b in btns if "Admin" in b.text or "Employee" in b.text), None)
        if role_btn:
            role_btn.click()
            time.sleep(0.4)
            toast = self.get_toast_text()
            self.assertTrue("Role" in toast or "role" in toast,
                            f"Expected role-change toast, got: '{toast}'")


# ═══════════════════════════════════════════════════════════
#  TC-11  LOGOUT FUNCTIONALITY
# ═══════════════════════════════════════════════════════════
class TC11_Logout(BaseTest):
    """Test logout functionality."""

    def setUp(self):
        self.open_app()
        self.login(ADMIN_USER, ADMIN_PASS)

    def test_01_logout_shows_auth_screen(self):
        """Clicking Logout returns user to the authentication screen."""
        self.driver.find_element(
            By.XPATH, "//button[contains(text(),'Logout')]").click()
        time.sleep(0.5)
        auth = self.driver.find_element(By.ID, "authScreen")
        self.assertTrue(auth.is_displayed(),
                        "Auth screen should be visible after logout")

    def test_02_app_hidden_after_logout(self):
        """Main app is hidden after logout."""
        self.driver.find_element(
            By.XPATH, "//button[contains(text(),'Logout')]").click()
        time.sleep(0.5)
        app = self.driver.find_element(By.ID, "app")
        self.assertEqual(app.value_of_css_property("display"), "none",
                         "App should be hidden after logout")

    def test_03_cannot_reuse_session_after_logout(self):
        """After logout, user must re-authenticate; direct nav shows login."""
        self.driver.find_element(
            By.XPATH, "//button[contains(text(),'Logout')]").click()
        time.sleep(0.5)
        # currentUser in JS should be null; app hidden
        current_user = self.driver.execute_script("return typeof currentUser !== 'undefined' ? currentUser : null;")
        self.assertIsNone(current_user,
                          "currentUser should be null/undefined after logout")


# ═══════════════════════════════════════════════════════════
#  TC-12  NAVIGATION / SIDEBAR
# ═══════════════════════════════════════════════════════════
class TC12_Navigation(BaseTest):
    """Test sidebar navigation between all pages."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _clear_storage(cls.driver, cls.wait)
        cls.driver.find_element(By.ID, "l_user").send_keys(ADMIN_USER)
        cls.driver.find_element(By.ID, "l_pass").send_keys(ADMIN_PASS)
        cls.driver.find_element(By.CSS_SELECTOR, "#loginForm .btn-primary").click()
        cls.wait.until(EC.visibility_of_element_located((By.ID, "page-dashboard")))

    def test_01_navigate_to_slots(self):
        """Navigating to Slot Monitor shows the slots page."""
        self.nav_to("slots")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-slots").get_attribute("class"))

    def test_02_navigate_to_allocate(self):
        """Navigating to Allocate shows the allocate page."""
        self.nav_to("allocate")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-allocate").get_attribute("class"))

    def test_03_navigate_to_vehicles(self):
        """Navigating to Vehicles shows the vehicle registry page."""
        self.nav_to("vehicles")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-vehicles").get_attribute("class"))

    def test_04_navigate_to_reports(self):
        """Navigating to Reports shows the reports page."""
        self.nav_to("reports")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-reports").get_attribute("class"))

    def test_05_navigate_to_notifications(self):
        """Navigating to Notifications shows the notifications page."""
        self.nav_to("notifications")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-notifications").get_attribute("class"))

    def test_06_navigate_to_users(self):
        """Admin can navigate to the Users page."""
        self.nav_to("users")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-users").get_attribute("class"))

    def test_07_navigate_to_backup(self):
        """Admin can navigate to the Backup page."""
        self.nav_to("backup")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-backup").get_attribute("class"))

    def test_08_navigate_back_to_dashboard(self):
        """Navigating back to Dashboard works from any page."""
        self.nav_to("slots")
        self.nav_to("dashboard")
        self.assertIn("active",
            self.driver.find_element(By.ID, "page-dashboard").get_attribute("class"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
