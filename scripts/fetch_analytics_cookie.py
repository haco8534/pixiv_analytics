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

    print(f"Fetching works for User ID: {my_id}")
    
    all_works = []
    
    try:
        url = f"https://www.pixiv.net/ajax/user/{my_id}/profile/all"
        res = requests.get(url, headers=headers)
        data = res.json()
        
        if data['error']:
            print(f"API Error: {data['message']}")
            return

        illust_ids = list(data['body']['illusts'].keys()) if data['body']['illusts'] else []
        manga_ids = list(data['body']['manga'].keys()) if data['body']['manga'] else []
        
        all_ids = illust_ids + manga_ids
        print(f"Found {len(all_ids)} works. Fetching details...")
        
        chunk_size = 50
        for i in range(0, len(all_ids), chunk_size):
            chunk_ids = all_ids[i:i+chunk_size]
            
            ids_param = "&".join([f"ids[]={id}" for id in chunk_ids])
            detail_url = f"https://www.pixiv.net/ajax/user/{my_id}/profile/illusts?{ids_param}&work_category=illustManga&is_first_page=0"
            
            time.sleep(1)
            
            res = requests.get(detail_url, headers=headers)
            detail_data = res.json()
            
            if not detail_data['error']:
                works = detail_data['body']['works']
                for work_id, work in works.items():
                    work_data = {
                        "id": work['id'],
                        "title": work['title'],
                        "type": work['illustType'], 
                        "create_date": work['createDate'],
                        "page_count": work['pageCount'],
                        "width": work['width'],
                        "height": work['height'],
                        "tags": work['tags'],
                        "total_view": work.get('viewCount', 0),
                        "total_bookmarks": work.get('bookmarkCount', 0),
                        "total_comments": work.get('commentCount', 0), 
                        "url": work['url']
                    }
                    all_works.append(work_data)
                print(f"  Fetched {len(all_works)}/{len(all_ids)} works...")
            else:
                print(f"  Error fetching chunk: {detail_data['message']}")

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
