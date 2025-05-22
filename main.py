try:
    import cv2
    import os
    import numpy as np
    import pytesseract
    from PIL import Image
    import time
    import hashlib
    import shutil
    import subprocess
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    input("\n🔚 프로그램을 종료하려면 Enter 키를 누르세요.")


SCREENSHOT_PATH = "screen.png"
PREVIOUS_SCREENSHOT_PATH = "screen_prev.png"
# 사용자 입력 받기
TARGET_PRICE = int(input("최소 클릭할 가격을 입력하세요 (예: 55000): "))

if not os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    print("⚠️ Tesseract가 설치되어 있지 않거나 경로가 잘못되었습니다.")
    input("아무키나 누르세요... ")
    exit()
    
# TARGET_PRICE = 50000
TARGET_CLICK_RATIO = (0.534, 0.16)  # 화면의 가로 50%, 세로 90%
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
def take_screenshot(save_as=SCREENSHOT_PATH):
    os.system("adb shell screencap -p /sdcard/screen.png")
    os.system(f"adb pull /sdcard/screen.png {save_as}")

def hash_image(image_path):
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def images_are_same(img1_path, img2_path):
    return hash_image(img1_path) == hash_image(img2_path)

def extract_prices(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, lang='kor+eng', output_type=pytesseract.Output.DICT)
    found = []

    for i, text in enumerate(data['text']):
        clean_text = text.replace(",", "").replace("\\", "").replace(" ", "").strip()
        # if "원" in clean_text:
        try:
            # '55,000원' → 55000
            price_str = ''.join(filter(str.isdigit, clean_text))
            price = int(price_str)
            
            if price >= TARGET_PRICE:
                x = data['left'][i]
                y = data['top'][i]
                found.append((price, x, y))
        except:
            continue
    return found

def click(x, y):
    os.system(f"adb shell input tap {x} {y}")

def get_screen_resolution():
    out = os.popen("adb shell wm size").read()
    # 예: "Physical size: 1080x1920\n"
    if "Physical size:" in out:
        parts = out.strip().split(":")[1].strip().split("x")
        return int(parts[0]), int(parts[1])
    return 1080, 1920  # 기본값

def click_relative(rx, ry):
    width, height = get_screen_resolution()
    x = int(rx * width)
    y = int(ry * height)
    print(f"🖱 비례 클릭 위치: {x}, {y}")
    click(x, y)

def scroll_down_slow():
    os.system("adb shell input swipe 3 1000 3 650 80")
    os.system("adb shell input swipe 2 1000 2 999 5")
    # os.system("adb shell input swipe 500 1500 500 700 400") 

def preprocess_image_for_ocr(img):
    # HSV 변환으로 파란색 배경 검출
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([140, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # 파란 배경 텍스트 추출
    blue_part = cv2.bitwise_and(img, img, mask=mask)

    # 그레이 변환 후 반전 → 글자가 밝아짐
    gray = cv2.cvtColor(blue_part, cv2.COLOR_BGR2GRAY)
    inverted = cv2.bitwise_not(gray)

    # 이진화
    _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def extract_text_data(img, lang='kor+eng'):
    processed_img = preprocess_image_for_ocr(img)
    data = pytesseract.image_to_data(
        processed_img,
        lang=lang,
        output_type=pytesseract.Output.DICT
    )
    return data

def find_and_click_text(image_path, target_text, threshold=0.8):
    """
    이미지에서 원하는 텍스트가 있으면 해당 위치를 클릭
    :param image_path: 이미지 경로
    :param target_text: 찾고 싶은 한글 또는 문자열 (예: "결제")
    :param threshold: OCR 유사도 임계값 (기본 0.8)
    """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)

    # OCR 데이터 (언어 kor 포함)
    data = pytesseract.image_to_data(gray, lang='kor+eng', output_type=pytesseract.Output.DICT)
    words_with_coords = []
    for i, text in enumerate(data['text']):
        clean = text.strip()
        if clean == "":
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        words_with_coords.append((x, y, w, h, clean))
    # 줄 단위로 병합 (Y좌표 기준)
    lines = []
    current_line = []
    last_y = None
    for x, y, w, h, text in sorted(words_with_coords, key=lambda item: (item[1], item[0])):
        if last_y is None or abs(y - last_y) < 25:
            current_line.append((x, y, w, h, text))
        else:
            lines.append(current_line)
            current_line = [(x, y, w, h, text)]
        last_y = y
    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines):
        line_sorted = sorted(line, key=lambda w: w[0])  # x 기준 정렬
        lines[i] = line_sorted
    
    for line in lines:
        line_text = "".join(word[4] for word in line)
        if target_text in line_text:
            print(f"✅ '{target_text}' 발견된 줄: {line_text}")
            # 클릭 좌표 계산 (중간 단어 기준)
            mid_word = line[len(line)//2]
            x_click = mid_word[0] + mid_word[2] // 2
            y_click = mid_word[1] + mid_word[3] // 2
            subprocess.run(["adb", "shell", "input", "tap", str(x_click), str(y_click)])
            return True

    print("❌ 원하는 텍스트를 찾을 수 없습니다.")
    return False



def main():
    
    while 1:
        scroll_count = 0
        max_scrolls = 10
        # take_screenshot(PREVIOUS_SCREENSHOT_PATH)

        while scroll_count < max_scrolls:
            take_screenshot(SCREENSHOT_PATH)
            prices = extract_prices(SCREENSHOT_PATH)

            if prices:
                price, x, y = prices[0]
                print(f"✅ {price}원 발견, 클릭 위치: ({x},{y})")
                click(x + 50, y + 50)
                # 나머지 작업
                find_and_click_text(SCREENSHOT_PATH, "동두천시")
                click_relative(*TARGET_CLICK_RATIO)
                break

            # 계속 스크롤
            print(f"🔄 조건 불충족. 스크롤 {scroll_count + 1}/{max_scrolls}")
            scroll_down_slow()
            scroll_count += 1
            time.sleep(0.1)
            take_screenshot(PREVIOUS_SCREENSHOT_PATH)

            # 이전 화면과 동일하면 비례 좌표 클릭
            if images_are_same(SCREENSHOT_PATH, PREVIOUS_SCREENSHOT_PATH):
                print("🔁 이전 화면과 동일: 더 이상 스크롤되지 않음")
                click_relative(*TARGET_CLICK_RATIO)
                break

        print("⛔ 조건 만족 가격 없음. 종료 또는 대체 처리 필요.")
    input("아무키나 누르세요... ")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    input("\n🔚 프로그램을 종료하려면 Enter 키를 누르세요.")
