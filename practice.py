# 安裝依賴
import os
import pymysql
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
from dotenv import load_dotenv

load_dotenv()

jawsdb_url = os.getenv("JAWSDB_URL")
url = urlparse(jawsdb_url)

DB_HOST = url.hostname
DB_USER = url.username
DB_PASSWORD = url.password
DB_NAME = url.path[1:]

connection = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)


def create_database_connection():
    """建立資料庫連接"""
    try:
        if connection.open:
            print("成功連接到 MySQL 資料庫")
            return connection
    except pymysql.MySQLError as e:
        print(f"連接到 MySQL 資料庫出錯: {e}")
        return None


def create_database_and_table():
    """創建資料庫和表格（如果不存在）"""
    try:
        if connection.open:
            cursor = connection.cursor()

            print("成功連接到 MySQL 伺服器")

            # 創建資料庫（如果不存在）
            # cursor.execute("CREATE DATABASE IF NOT EXISTS book_scraper")
            # print("資料庫 'book_scraper' 已確認存在")

            # 切換到該資料庫
            cursor.execute(f"USE {DB_NAME}")

            print("成功切換到資料庫")

            # 創建書籍表格
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    image_url VARCHAR(255),
                    price VARCHAR(50),
                    rating VARCHAR(20),
                    detail_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("表格 'books' 已確認存在")

            connection.close()
            return True

    except pymysql.MySQLError as e:
        print(f"設置資料庫時出錯: {e}")
        return False


def fetch_webpage(url):
    """獲取網頁內容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/96.0.4664.110 Safari/537.36"
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
    """解析HTML內容，提取書籍內容"""
    if not html_content:
        print("HTML內容為空，無法解析")
        return []

    print("開始解析HTML內容...")
    soup = BeautifulSoup(html_content, "html.parser")
    books = []

    # 使用CSS選擇器找到元素
    # books.toscrape.com 的書籍都在 article.product_pod 元素中
    book_elements = soup.select("article.product_pod")
    print(f"找到 {len(book_elements)} 本書籍")

    for index, book in enumerate(book_elements):
        try:
            print(f"正在解析第 {index+1} 本書籍...")

            # 提取書籍標題
            title = book.select_one("h3 a").get("title")

            # 提取書籍圖片URL
            image_url = book.select_one("img").get("src")
            if image_url and not image_url.startswith("http"):
                # 補全相對URL
                if image_url.startswith(".."):
                    image_url = f"http://books.toscrape.com/{image_url[3:]}"
                else:
                    image_url = f"http://books.toscrape.com/{image_url}"

            # 提取書籍價格
            price = book.select_one("p.price_color").text

            # 提取書籍評分
            rating = book.select_one("p.star-rating").get("class")[-1]

            # 提取書籍細節頁面URL
            detail_url = book.select_one("h3 a").get("href")
            if detail_url and not detail_url.startswith("http"):
                base_url = "http://books.toscrape.com/catalogue/"
                if detail_url.startswith(".."):
                    detail_url = f"{base_url}{detail_url[3:]}"
                else:
                    detail_url = f"{base_url}{detail_url}"

            # 儲存書籍內容
            books.append(
                {
                    "title": title,
                    "image_url": image_url,
                    "price": price,
                    "rating": rating,
                    "detail_url": detail_url,
                }
            )
            print(f"成功解析書籍: {title}")
        except Exception as e:
            print(f"解析第 {index+1} 本書籍時出錯: {e}")

    return books


def save_to_database(books):
    """將書籍資料保存到資料庫"""
    if not books:
        print("沒有書籍資料可保存")
        return 0

    getConnection = create_database_connection()
    if not getConnection:
        return 0

    try:
        cursor = getConnection.cursor()

        # 準備 SQL 插入語句
        insert_query = """
            INSERT INTO books (title, image_url, price, rating, detail_url)
            VALUES (%s, %s, %s, %s, %s)
        """

        # 批量插入資料
        book_tuples = [(book["title"], book["image_url"], book["price"],
                        book["rating"], book["detail_url"]) for book in books]

        cursor.executemany(insert_query, book_tuples)
        connection.commit()

        inserted_count = cursor.rowcount
        print(f"成功將 {inserted_count} 本書籍保存到資料庫")

        return inserted_count

    except pymysql.MySQLError as e:
        print(f"保存到資料庫時出錯: {e}")
        return 0
    finally:
        if getConnection.open:
            cursor.close()
            connection.close()
            print("資料庫連接已關閉")


def main():
    """主函數: 協調整個爬蟲流程"""
    all_books = []

    print("=" * 50)
    print("書籍爬蟲程序啟動")
    print("=" * 50)

    if not create_database_and_table():
        print("設置資料庫失敗，程式終止")
        return

    total_pages = 50

    for page in range(1, total_pages + 1):
        # 書籍網站URL
        book_url = f"http://books.toscrape.com/catalogue/page-{page}.html"
        print(f"\n正在爬取第 {page} 頁的書籍內容...")
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
            print("無法獲取網頁內容，請檢查網址或網絡連接")

    # 步驟3: 保存數據到資料庫
    if all_books:
        print("\n步驟3: 保存提取的數據到資料庫")
        print("-" * 30)
        print(f"共爬取到 {len(all_books)} 本書籍的內容")

        # 輸出摘要內容
        print("\n爬取結果摘要:")
        print("-" * 30)
        for i, book in enumerate(all_books[:3], 1):
            print(
                f"書籍 {i}: {book['title']}"
                f"(£{book['price']}) - {book['rating']}星評價"
            )
        if len(all_books) > 3:
            print(f"... 以及其他 {len(all_books) - 3} 本書籍")
    else:
        print("未找到任何書籍內容")

    print("\n執行完成")


if __name__ == "__main__":
    # 程序入口點
    main()
