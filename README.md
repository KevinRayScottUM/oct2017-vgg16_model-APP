# VGG16 OCT_2017 Retina Diagnosis WebApp  
VGG16 OCT_2017 视网膜 OCT 智能诊断 Flask Web 项目

---

## 1. Project Overview / 项目简介

This repository provides a complete web application for **automatic classification of retinal OCT images** using a fine-tuned **VGG16-BN** model.  
User can register/login, upload a retinal OCT image through a drag-and-drop web interface, and receive an AI diagnosis in real time.

本项目是一个基于 **Flask + PyTorch** 的 **OCT 视网膜疾病智能诊断系统**。  
用户可以在网页端完成 **注册 / 登录 / 图片上传 / AI 诊断 / 结果保存与查看** 等完整流程。

The model outputs one of four categories:

- **脉络膜新生血管 [CNV]**
- **糖尿病性黄斑水肿 [DME]**
- **玻璃膜疣 [DRUSEN]**
- **无异常 [NORMAL]**

---

## 2. Tech Stack / 技术栈

**Backend / 后端**

- Python 3.x
- Flask
- gevent (`WSGIServer` for production-style serving)
- PyTorch & Torchvision (VGG16-BN model)
- Pillow (image loading & preprocessing)
- SQLite database (`flask-layui.sqlite`) + custom `db.py` wrapper
- Session, CAPTCHA & simple SMS-style verification logic

**Frontend / 前端**

- HTML5 templates (Flask `templates/`)
- jQuery + Bootstrap + LayUI (from `static/js` and `static/css`)
- Custom JavaScript upload & preview logic in `static/js/main.js`

---

## 3. Project Structure / 项目目录结构

Approximate layout:

```text
VGG-16 OCT_2017/
└── vgg-16-flask-webapp/
    ├── app.py                 # Flask entrypoint & HTTP routes
    ├── db.py                  # Database helpers (user + result storage)
    ├── get_captcha.py         # Graphical captcha generation
    ├── util.py                # Utility functions
    ├── flask-layui.sqlite     # SQLite database file
    ├── Dockerfile             # Optional Docker deployment
    ├── models/
    │   └── VGG16_OCT_Retina_trained_model.pt  # Trained VGG16-BN weights
    ├── static/
    │   ├── js/
    │   │   ├── main.js        # Frontend upload + /predict integration
    │   │   └── ...            # jQuery, Bootstrap, etc.
    │   ├── css/               # Stylesheets
    │   └── img/               # Static images, icons, etc.
    ├── templates/
    │   ├── index.html         # Home page
    │   ├── AIDiagnose.html    # AI diagnosis page
    │   ├── Login.html         # Login page
    │   ├── register.html      # Register page
    │   ├── Info.html          # Personal center / history
    │   └── about.html         # About page
    └── uploads/               # (Optional) temporary upload directory
```

> 目录名可能会根据你本地项目略有差异，上述仅为逻辑结构说明。

---

## 4. Core Features / 核心功能说明

### 4.1 User System / 用户系统

- **Registration / 用户注册**  
  - Endpoint: `POST /api/register`  
  - Validates SMS-style verification code (`vercode`) stored in session.  
  - Stores `nickname`, `mobile`, `password` (and an empty `result`) via `Database().insert(...)`.

- **Login / 用户登录**  
  - Endpoint: `POST /api/login`  
  - Uses mobile + password + graphical CAPTCHA (`/get_captcha`) validation.  
  - On success sets session keys: `is_login`, `mobile`, `username`.

- **Logout / 退出登录**  
  - Endpoint: `GET /logout`  
  - Clears session and redirects to `index`.

- **Password Change / 修改密码**  
  - Endpoint: `POST /api/change_password_check`  
  - Reads `new_password` from JSON body, uses `session['mobile']` to update DB.  
  - Returns JSON message (`code=0` on success).

- **Login Status Check / 登录状态检查**  
  - Endpoint: `GET /check_login`  
  - Returns `{ "is_login": true/false }` so frontend can adapt UI.

- **CAPTCHA / 图形验证码**  
  - Endpoint: `GET /get_captcha?captcha_uuid=...`  
  - Uses `get_captcha_code_and_content` to generate an image;  
  - Stores the generated code in `session['code']` and returns PNG bytes.

### 4.2 Pages / 页面路由

- `GET /` – Home page (`index.html`)  
  - If logged in, passes `username` from DB to template.

- `GET /Info` – Personal information & last result (`Info.html`)  
  - Shows `username`, `phone`, and last `result` fetched by `db.search_info(mobile)`.

- `GET /AIDiagnose` – AI diagnosis page (`AIDiagnose.html`)  
  - Displays current user info + latest diagnosis result if logged in.

- `GET /register` – Render registration page.  
- `GET /login` – Render login page.  
- `GET /change_password` – Render password-change page.  
- `GET /about` – About page.

### 4.3 AI Diagnosis API / AI 诊断接口

**Endpoint: `POST /predict`**

1. Expects an uploaded image file under key `"file"` (JPEG/JPG).  
2. Chooses an appropriate device:

   - `cuda` if an NVIDIA GPU is available  
   - Apple `mps` if available  
   - otherwise falls back to CPU

3. Applies preprocessing:

   - Resize to 256 → center crop 224×224  
   - Convert to tensor, add batch dimension  
   - Move tensor to the selected device  

4. Builds VGG16-BN model:

   - `models.vgg16_bn()`  
   - Replace last classifier layer with `nn.Linear(4096, 4)`  
   - Load weights from `models/VGG16_OCT_Retina_trained_model.pt`  
   - `eval()` mode, no gradient

5. Runs inference and maps the predicted index to human-readable label:

   ```python
   category_mapping = [
       '脉络膜新生血管 [CNV]',
       '糖尿病性黄斑水肿 [DME]',
       '玻璃膜疣 [DRUSEN]',
       '无异常 [NORMAL]'
   ]
   ```

6. If the user is logged in, saves the textual result for this user via `db.insert_result(...)`.

7. Returns JSON:

   ```json
   {
     "result_new_model": 0,
     "vgg16": "脉络膜新生血管 [CNV]"
   }
   ```

**Endpoint: `POST /save_result`**

- Accepts JSON `{ "result": "<string>" }` and persistently stores it in the DB.  
- Used when you want to explicitly save one diagnosis result.

---

## 5. Frontend Logic (`main.js`) / 前端逻辑

The frontend provides a smooth drag-and-drop experience for uploading images:

- `fileDrag` and `fileSelect` DOM elements handle drag-and-drop or manual selection.  
- `previewFile(file)` shows a client-side preview and sends a Base64 data URL to `displayImage`.  
- `submitImage()`:
  - Ensures an image has been selected.  
  - Shows a loader animation.  
  - Converts the Base64 image to a `Blob` and wraps it into `FormData` as field `"file"`.  
  - Sends `fetch("/predict", { method: "POST", body: formData })`.  
- On success, `displayResult(data)`:
  - Hides the loader.  
  - Displays **“诊断结果为: <分类结果>”**.  
  - Pops up an alert and then reloads the page after a short countdown so the user list/history can be refreshed.  
- `clearImage()` resets file input, hides preview/result and restores the upload caption.

---

## 6. How to Run / 本地运行方式

### 6.1 Environment / 环境准备

1. Install Python 3.8+.  
2. Create and activate a virtual environment (推荐):

   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   # 或
   venv\Scripts\activate           # Windows
   ```

3. Install dependencies (示例):

   ```bash
   pip install flask gevent torch torchvision pillow
   ```

   > If you have a specific `requirements.txt`, prefer:  
   > `pip install -r requirements.txt`

4. Ensure the trained model file exists:

   ```text
   vgg-16-flask-webapp/models/VGG16_OCT_Retina_trained_model.pt
   ```

### 6.2 Start the Server / 启动服务

In the project root where `app.py` is located:

```bash
python app.py
```

The script will:

- Create `uploads/` folder if needed.  
- Start a `gevent.pywsgi.WSGIServer` on `0.0.0.0:5000`.  
- Automatically open `http://127.0.0.1:5000/` in your default browser.

---

## 7. Basic Usage Flow / 使用流程

1. **访问首页**：浏览器打开 `http://127.0.0.1:5000/`。  
2. **注册账号**：进入注册页，填入昵称、手机号、密码，获取并填写短信验证码完成注册。  
3. **登录系统**：在登录页输入手机号、密码和图形验证码。  
4. **上传图像诊断**：  
   - 进入 “AI 智能诊断” 页面；  
   - 拖拽或选择一张 OCT 视网膜图像；  
   - 点击 “开始诊断” 按钮等待 AI 返回结果。  
5. **查看与保存结果**：  
   - 前端弹出 “诊断结果为: …” 的提示；  
   - 结果会保存到当前登录用户的数据库记录中；  
   - 在 “个人信息 / Info” 页面可以查看历史检测结果和个人信息。  

---

## 8. Deployment with Docker (Optional) / 使用 Docker 部署（可选）

If you want to deploy with Docker, you can roughly:

```bash
docker build -t vgg16-oct-webapp .
docker run -p 5000:5000 vgg16-oct-webapp
```

(Details depend on the actual `Dockerfile` contents.)

---

## 9. Notes & TODO / 备注与后续改进

- Current implementation loads the VGG16 model on each `/predict` call;  
  for high-traffic scenarios you may want to **load the model once at startup** and reuse it.  
- The SMS verification logic is simulated; for production you should integrate a real SMS provider.  
- Passwords should be stored using proper hashing (e.g. `werkzeug.security`), not plain text.  
- Add unit tests and better error handling for robustness.

---

## 10. License / 许可证

Add your chosen license here (e.g. MIT, Apache-2.0).  

> 示例：  
> This project is licensed under the MIT License – see the `LICENSE` file for details.
