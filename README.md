# miso
1. adb 설치후 환경변수 설정
2. 파이썬 설치
3. 파이썬 라이브러리 설치 pip install pytesseract pillow numpy
pip install opencv-python==4.5.5.64
pip install scikit-image
4. 테서렉트 설치 https://github.com/tesseract-ocr/tesseract/releases/
5. 테서렉트 환경변수 설정
6. https://github.com/tesseract-ocr/tessdata 한글파일 다운로드 후 C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata 넣기
7. pyinstaller --onefile --hidden-import=cv2 main.py
8.안될땐 관리자권항으로 vscode 실행,cmd실행