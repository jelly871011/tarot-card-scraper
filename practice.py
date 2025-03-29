# 安裝依賴
import requests
from bs4 import BeautifulSoup
import json
import time
import os

def fetch_webpage(url):
    """獲取網頁內容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    }
    
    try:
        print(f"正在發送請求到: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("請求成功，獲取到網頁內容")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"獲取網頁出錯: {e}")
        return None

def parse_books(html_content):
    """解析HTML內容，提取書籍信息"""
    if not html_content:
        print("HTML內容為空，無法解析")
        return []
    
    print("開始解析HTML內容...")
    soup = BeautifulSoup(html_content, 'html.parser')
    books = []
    
    # 使用CSS選擇器定位書籍元素
    # books.toscrape.com 的書籍都在 article.product_pod 元素中
    book_elements = soup.select('article.product_pod')
    print(f"找到 {len(book_elements)} 本書籍")
    
    for index, book in enumerate(book_elements):
        try:
            print(f"正在解析第 {index+1} 本書籍...")
            
            # 提取書籍標題
            title = book.select_one('h3 a').get('title')
            
            # 提取書籍圖片URL
            image_url = book.select_one('img').get('src')
            if image_url and not image_url.startswith('http'):
                # 補全相對URL
                if image_url.startswith('..'):
                    image_url = f"http://books.toscrape.com/{image_url[3:]}"
                else:
                    image_url = f"http://books.toscrape.com/{image_url}"
            
            # 提取書籍價格
            price = book.select_one('p.price_color').text
            
            # 提取書籍評分
            rating = book.select_one('p.star-rating').get('class')[-1]
            
            # 提取書籍詳情頁面URL
            detail_url = book.select_one('h3 a').get('href')
            if detail_url and not detail_url.startswith('http'):
                # 補全相對URL
                if detail_url.startswith('..'):
                    detail_url = f"http://books.toscrape.com/catalogue/{detail_url[3:]}"
                else:
                    detail_url = f"http://books.toscrape.com/catalogue/{detail_url}"
            
            # 將提取的信息組織為字典並添加到結果列表
            books.append({
                'title': title,
                'image_url': image_url,
                'price': price,
                'rating': rating,
                'detail_url': detail_url
            })
            print(f"成功解析書籍: {title}")
        except Exception as e:
            print(f"解析第 {index+1} 本書籍時出錯: {e}")
    
    return books

def save_to_json(data, filename='books.json'):
    """將數據保存為JSON文件"""
    print(f"準備將數據保存到 {filename}...")
    # 確保輸出目錄存在
    os.makedirs(os.path.dirname(os.path.abspath(filename)) or '.', exist_ok=True)
    
    # 寫入JSON文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"數據已成功保存至 {filename}")

def main():
    """主函數: 協調整個爬蟲流程"""
     # 準備存放所有書籍的列表
    all_books = []

    output_file = "books.json"

    print("=" * 50)
    print("書籍爬蟲程序啟動")
    print("=" * 50)

    total_pages = 5

    for page in range(1, total_pages + 1):
        # 書籍網站URL
        book_url = f"http://books.toscrape.com/catalogue/page-{page}.html"
        print(f"\n正在爬取第 {page} 頁的書籍信息...")
        print("-" * 50)

        # 步驟1: 獲取網頁內容
        print("\n步驟1: 獲取網頁內容")
        print("-" * 30)
        html_content = fetch_webpage(book_url)
        
        if html_content:
            # 步驟2: 解析網頁內容
            print("\n步驟2: 解析網頁內容")
            print("-" * 30)
            books = parse_books(html_content)
            
            if books:
                print(f"在第 {page} 頁找到 {len(books)} 本書籍")
                all_books.extend(books)  # 將本頁的書籍添加到總列表中
            else:
                print(f"第 {page} 頁未找到任何書籍，可能已到達最後一頁")
                break  # 如果沒有找到書籍，可能已經到達最後一頁，停止爬取
            
            # 添加延遲，避免頻繁請求
            if page < total_pages:
                delay = 1  # 延遲1秒
                print(f"等待 {delay} 秒後繼續爬取下一頁...")
                time.sleep(delay)
            else:
                print("未找到任何書籍信息，請檢查網站結構或選擇器")
        else:
            print("無法獲取網頁內容，請檢查網址或網絡連接")
        
        # 步驟3: 保存數據到JSON文件
        if all_books:
            output_file = f"books_{total_pages}pages.json"
            print(f"\n步驟3: 保存提取的數據")
            print("-" * 30)
            print(f"共爬取到 {len(all_books)} 本書籍的信息")
            save_to_json(all_books, output_file)
        
            # 輸出摘要信息
            print("\n爬取結果摘要:")
            print("-" * 30)
            for i, book in enumerate(all_books[:3], 1):
                print(f"書籍 {i}: {book['title']} (£{book['price']}) - {book['rating']}星評價")
            if len(all_books) > 3:
                print(f"... 以及其他 {len(books) - 3} 本書籍")
        
        print("\n爬蟲程序執行完成")

if __name__ == "__main__":
    # 程序入口點
    main()