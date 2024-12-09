from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd


base_url='https://pve.proxmox.com/pve-docs/api-viewer/index.html'

# 設定 edge 選項
edge_options = webdriver.EdgeOptions()
edge_options.add_argument('--no-sandbox')  # 提高穩定性
edge_options.add_argument('--disable-dev-shm-usage')  # 避免記憶體問題
edge_options.add_argument('--disable-gpu')  # 降低GPU使用

def get_parameter():
        parameter={}
        parameter_descriptions = {}
        parameters_rows = driver.find_elements(By.XPATH, '//div[text()="Parameters"]/ancestor::*[5]//tr[@role="row"]')
        for row in parameters_rows:
            try:
                name = row.find_element(By.XPATH, './/td[1]//div').text.strip()
                type_ = row.find_element(By.XPATH, './/td[2]//div').text.strip()
                description = row.find_element(By.XPATH, './/td[last()]//div').text.strip()  # 提取參數描述
                if name and type_:
                    parameter[name] = type_
                    parameter_descriptions[name] = description
            except Exception as e:
                pass  # 忽略無效行
        return parameter, parameter_descriptions

def get_api_info(nodes:list[WebElement],error_catch:list=None):
    result=pd.DataFrame(columns=columns)
    len_=len(nodes)
    conunt=0
    for node in nodes:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", node)
            wait.until(EC.element_to_be_clickable(node))
            node.click()
        except Exception as e:
            print(f'Error occurred for node: {node.text if node.is_enabled() else "Unknown"}')
            print(f'Error details: {str(e)}')
            if error_catch is not None:
                error_catch.append(node)
            continue
        tabs = driver.find_elements(By.XPATH,'//a[@role="tab"]')
        api_info=['']*len(tabs)
        for i,e in enumerate(tabs):
            e.click()
            usages = driver.find_elements(By.XPATH,'//td[contains(text(),"HTTP")]/../td[2]')
            descriptions = driver.find_elements(By.XPATH,'//div[text()="Description"]/ancestor::*[5]//div[@class="x-autocontainer-innerCt"]')
            methods = [usage.text for usage in usages]
            parameters, parameter_descriptions = get_parameter()
            # route[i] = methods[i]
            api_info[i] = {
                'Path':methods[i].split(' ')[1],
                'Method':methods[i].split(' ')[0],
                'Description':descriptions[i].text,
                'Parameters':parameters,
                'Parameter Details':parameter_descriptions
            }
        # api_info = pd.DataFrame(api_info)
        result = pd.concat([result,pd.DataFrame(api_info)],ignore_index=True)
        conunt+=1
        print(f'當前範圍已處理:{conunt}/{len_}',flush=True,end='\r')
    return result


if __name__ == '__main__':
    # 啟動 edge 瀏覽器
    block=1
    driver = webdriver.Edge(options=edge_options)
    driver.get(base_url)

    # 建立API總表
    columns = ['Path','Method','Description','Parameters','Parameter Details']
    api_table = pd.DataFrame(columns=columns)

    # 等待頁面完全載入
    wait = WebDriverWait(driver, 3)
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"x-tool-expand")]')))
    driver.find_element(By.XPATH,'//div[@id="tool-1017-toolEl"]').click()

    # 初始化節點範圍
    print('初始化節點範圍')
    nodes = driver.find_elements(By.XPATH,'//span[@class="x-tree-node-text "]')
    last_node = nodes[-1]
    
    # 捕獲錯誤節點
    error_list=[]
    while True:
        # 取得範圍內API資訊
        insert_table = get_api_info(nodes,error_catch=error_list)
        
        # 將API資訊加入總表
        api_table = pd.concat([api_table,insert_table],ignore_index=True)

        # 重新取得節點範圍
        print('\n重新取得節點範圍',block)
        nodes = driver.find_elements(By.XPATH,'//span[@class="x-tree-node-text "]')
        if last_node in nodes:
            nodes = nodes[nodes.index(last_node)+1:]
        if len(nodes)>0:
            last_node = nodes[-1]
            block+=1
        if len(nodes)==0:
            break
    print('API資訊爬取完成')
    api_table.to_csv('proxmox_api.csv',index=False)
    driver.quit()


