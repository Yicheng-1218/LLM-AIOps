from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
def get_pve_screenshot(save_path):
    # 設定 edge 選項
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument('--no-sandbox')  # 提高穩定性
    edge_options.add_argument('--disable-dev-shm-usage')  # 避免記憶體問題
    edge_options.add_argument('--disable-gpu')  # 降低GPU使用
    edge_options.add_argument('--ignore-certificate-errors')  # 忽略憑證錯誤
    edge_options.add_argument('--headless')  # 隱藏視窗


    driver = webdriver.Edge(options=edge_options)


    driver.get('https://192.168.194.128:8006/')


    result = driver.execute_script(
    """
    return new Promise((resolve, reject) => {
        let url = 'https://192.168.194.128:8006/api2/extjs/access/ticket';
        let data = {
            username: 'agent',
            password: '12345',
            realm: 'pve'
        };
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(data)
        })
        .then(response => response.json())
        .then(data => resolve(data))
        .catch(error => reject(error));
    });
    """)

    # 設定必要的 cookies 和 localStorage
    driver.execute_script(
    f"""
    // 設定 PVEAuthCookie
    document.cookie = "PVEAuthCookie=" + '{result["data"]["ticket"]}' + "; path=/";
    // 設定 CSRFPreventionToken
    localStorage.setItem('CSRFPreventionToken', '{result["data"]["CSRFPreventionToken"]}');
    """
    )

    # 重新載入頁面
    driver.refresh()
    # 等待狀態面板載入完成
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id,"pveStatusPanel") and @data-ref="body"]'))
        )
        result = driver.get_screenshot_as_file(save_path)
        return result
    except TimeoutException:
        print("等待狀態面板載入超時")
        driver.quit()
        return False
    finally:
        driver.quit()
    


