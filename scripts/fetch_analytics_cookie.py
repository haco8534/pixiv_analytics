import os
import json
import datetime
import time
import requests

# 環境変数からPHPSESSIDを取得
PHPSESSID = os.environ.get("PIXIV_PHPSESSID")

def main():
    if not PHPSESSID:
        print("Error: PIXIV_PHPSESSID is not set.")
        return
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": f"PHPSESSID={PHPSESSID}",
        "Referer": "https://www.pixiv.net/"
    }

    # ユーザーIDが未設定の場合、PHPSESSIDから抽出を試みる
    my_id = None
    print("Extracting user ID from PHPSESSID...")
    # PHPSESSIDのフォーマットは "USER_ID_RANDOMSTRING"
    if "_" in PHPSESSID:
        my_id = PHPSESSID.split("_")[0]
        if my_id.isdigit():
            print(f"Detected User ID: {my_id}")
        else:
            print("Could not extract numeric ID from PHPSESSID.")
            return
    else:
        print("Invalid PHPSESSID format. Cannot extract User ID.")
        return

    print(f"Fetching works for User ID: {my_id} (Dashboard Analysis API)")
    
    all_works = []
    
    try:
        # アナリティクス用のAPIがあるはず
        # ajax/user/{id}/profile/all でID一覧を取得し、その後に詳細を取得する方式に戻すが、
        # "manage/illusts" のAPIが使えないなら、個別に "ajax/illust/{id}" を叩くのが確実かもしれない。
        # ただし件数が多いと遅い。
        
        # もう一度 profile/all を試すが、Cookieが効いているか確認するために
        # "ajax/user/extra" を叩いてログイン状態を確認する。
        
        res = requests.get("https://www.pixiv.net/ajax/user/extra", headers=headers)
        if res.status_code != 200:
            print(f"Login Check Failed: Status {res.status_code}")
            return
            
        extra_data = res.json()
        if extra_data['error']:
            print("Login Check Failed: API Error")
            # ログインしていないとみなされている可能性大
        else:
            print("Login Check OK.")

        # 作品一覧取得（ページネーションなしで全IDが取れるのが特徴）
        url = f"https://www.pixiv.net/ajax/user/{my_id}/profile/all"
        res = requests.get(url, headers=headers)
        data = res.json()
        
        if data['error']:
            print(f"API Error: {data['message']}")
            return

        illust_ids = list(data['body']['illusts'].keys()) if data['body']['illusts'] else []
        manga_ids = list(data['body']['manga'].keys()) if data['body']['manga'] else []
        all_ids = illust_ids + manga_ids
        
        print(f"Found {len(all_ids)} works. Fetching details via Individual API...")
        
        # まとめて取得するAPIが統計を返さないなら、1つずつ叩くしかない
        # https://www.pixiv.net/ajax/illust/{id}
        
        count = 0
        for wid in all_ids:
            # 高速化のため、最初の50件だけにする？いや、全件取得したいはず。
            # 少しウェイトを入れないとBANされる
            time.sleep(0.5) 
            
            url = f"https://www.pixiv.net/ajax/illust/{wid}"
            res = requests.get(url, headers=headers)
            w_data = res.json()
            
            if w_data['error']:
                print(f"Error fetching work {wid}: {w_data['message']}")
                continue
                
            work = w_data['body']
            
            work_data = {
                "id": str(work['illustId']),
                "title": work['illustTitle'],
                "type": int(work['illustType']), 
                "create_date": work['createDate'],
                "page_count": int(work['pageCount']),
                "width": int(work['width']),
                "height": int(work['height']),
                "tags": [t['tag'] for t in work['tags']['tags']],
                "total_view": int(work['viewCount']),
                "total_bookmarks": int(work['bookmarkCount']),
                "total_comments": int(work['commentCount']), 
                "url": work['urls']['small'] 
            }
            all_works.append(work_data)
            count += 1
            
            if count % 10 == 0:
                print(f"  Fetched {count}/{len(all_ids)} works...")

    except Exception as e:
        print(f"Critial Error: {e}")
        import traceback
        traceback.print_exc()

    print(f"Total works fetched: {len(all_works)}")

    if all_works:
        save_data(all_works)
    else:
        print("No works found or fetch failed.")

def save_data(new_works):
    data_dir = os.path.join(os.getcwd(), "data")
    file_path = os.path.join(data_dir, "analytics_history.json")
    
    os.makedirs(data_dir, exist_ok=True)
    
    history = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    
    snapshot = {
        "timestamp": datetime.datetime.now().isoformat(),
        "works": new_works
    }
    
    history.append(snapshot)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"Saved snapshot to {file_path}. Total snapshots: {len(history)}")

if __name__ == "__main__":
    main()
