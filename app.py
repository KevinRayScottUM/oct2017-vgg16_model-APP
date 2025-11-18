# 导入其他必要的库
from flask import Flask, request, render_template, jsonify, redirect, session, make_response, url_for
from gevent.pywsgi import WSGIServer
from torchvision import transforms
from PIL import Image
from torchvision import models
import torch.nn as nn
import torch
import os
from torch.autograd import Variable
import webbrowser
import threading
from get_captcha import get_captcha_code_and_content
from db import Database, db
import re
import logging
import random

app = Flask(__name__)
app.secret_key = 'notes.zhengxinonly.com'

print('Model Will Be Prepared After You Check http://127.0.0.1:5000/')

# 在 model_predict 函数中添加以下打印语句
def model_predict(img_path, model):
    # 加载并预处理图像
    print("Image Path:", img_path)

    img = Image.open(img_path).convert('RGB')

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    img_tensor = transform(img).unsqueeze(0)

    # 将输入数据移动到相同的设备上
    device = next(model.parameters()).device
    img_tensor = img_tensor.to(device)

    # 使用模型进行预测
    with torch.no_grad():
        model.eval()
        preds = model(img_tensor)

    print("Predictions:", preds)
    _, predicted_class = torch.max(preds, 1)
    result = int(predicted_class)
    print("Predicted Result:", result)

    return preds
@app.route('/')
def index():
    is_login = session.get('is_login')
    username = None  # 默认用户名为空
    if is_login:
        # 如果已登录，从数据库中获取用户名
        mobile = session.get('mobile')  # 假设您的会话中包含用户手机号
        username = db.search1(mobile)  # 从数据库中获取用户名
    return render_template('index.html', is_login=is_login, username=username)
@app.route('/Info')
def Info():
    is_login = session.get('is_login')
    username = None  # 默认用户名为空
    phone = None # 默认电话为空
    result = None  # 默认检测结果为空
    if is_login:
        # 如果已登录，从数据库中获取用户名和检测结果
        mobile = session.get('mobile')  # 假设您的会话中包含用户手机号
        username, result, phone= db.search_info(mobile)  # 从数据库中获取用户名和检测结果
    return render_template('Info.html', is_login=is_login, username=username, phone=phone, result=result)

@app.route('/LoginIndex')
def LoginIndex():
    # 这里是端点处理逻辑
    pass

@app.route('/register')
def register():
    return render_template('register.html')
@app.route('/login')
def login():
    return render_template('Login.html')
@app.route('/change_password')
def change_password():
    return render_template('change_password.html')
# 修改密码接口
@app.route('/api/change_password_check', methods=['POST'])
def change_password_check():
    data = request.get_json()
    new_password = data.get('new_password')

    # 获取当前登录用户的手机号
    mobile = session.get('mobile')
    if not mobile:
        return jsonify(message="User not logged in", code=-1)

    # 更新密码
    db.update_password(mobile, new_password)

    return jsonify(message="Password changed successfully", code=0)


@app.post('/api/send_register_sms')
def send_register_sms():
    # 1. 解析前端传递过来的数据
    data = request.get_json()
    mobile = data['mobile']

    # 2. 校验手机号码(正则表达式)
    pattern = r'^1[3-9]\d{9}$'
    ret = re.match(pattern, mobile)
    if not ret:
        return {
            'message': '电话号码不符合格式',
            'code': -1
        }

    # 3. 发送短信验证码，并记录
    session['mobile'] = mobile

    # 3.1 生成随机验证码
    code = random.choices('123456789', k=6)
    session['code'] = ''.join(code)
    logging.warning(''.join(code))
    return {
        'message': '发送短信成功',
        'code': 0
    }

@app.post('/api/register')
def register_api():
    # 1. 解析前端传递过来的数据
    data = request.get_json()
    vercode = data['vercode']
    vercode2 = session['code']
    if vercode != vercode2:
        return {
            'message': '短信验证码错误',
            'code': -1
        }

    nickname = data['nickname']
    mobile = data['mobile']
    password = data['password']
    if not all([nickname, mobile, password]):
        return {
            'message': '数据缺失',
            'code': -1
        }
    Database().insert(nickname, mobile, password, result=None)
    return {
        'message': '注册用户成功',
        'code': 0
    }

@app.get('/get_captcha')
def get_captcha_view():
    # 1. 获取参数
    captcha_uuid = request.args.get("captcha_uuid")
    # 2. 生成验证码
    code, content = get_captcha_code_and_content()

    # 3. 记录数据到数据库（用session代替）
    session['code'] = code
    resp = make_response(content)  # 读取图片的二进制数据做成响应体
    resp.content_type = "image/png"
    # 4. 错误处理

    # 5. 响应返回
    return resp
@app.route('/check_login')
def check_login():
    is_login = session.get('is_login')
    return jsonify(is_login=is_login)

@app.post('/api/login')
def login_api():
    data = request.get_json()
    code = session['code']
    if code != data['captcha']:
        return {
            'message': '验证码错误',
            'code': -1
        }
    ret = Database().search(data['mobile'])
    if not ret:
        return {
            'message': '用户不存在',
            'code': -1
        }
    pwd = ret[0]
    if pwd != data['password']:
        return {
            'message': '用户密码错误',
            'code': -1
        }
    session['is_login'] = True  # 记录用户登录
    session['mobile'] = data['mobile']  # 记录用户手机号码
    session['username'] = ret[0]  # 记录用户名
    return {
        'message': '用户登录成功',
        'code': 0
    }
@app.route('/logout', methods=['GET'])
def logout():
    # 清除会话信息
    session.pop('is_login', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('mobile', None)  # 清除手机号码信息

    # 重定向到登录页面或其他需要的页面
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/AIDiagnose', methods=['GET'])
def AIDiagnose():
    is_login = session.get('is_login')
    username = None  # 默认用户名为空
    phone = None  # 默认电话为空
    result = None  # 默认检测结果为空
    if is_login:
        # 如果已登录，从数据库中获取用户名和检测结果
        mobile = session.get('mobile')  # 假设您的会话中包含用户手机号
        username, result, phone = db.search_info(mobile)  # 从数据库中获取用户名和检测结果
    return render_template('AIDiagnose.html', is_login=is_login, username=username, phone=phone, result=result)

# 修改服务端返回 JSON 格式
@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify(error="No file part")

    file = request.files['file']

    if file.filename == '':
        return jsonify(error="No selected file")

    if file:
        model_path = 'models/VGG16_OCT_Retina_trained_model.pt'
        # 设置设备为GPU（如果可用）
        if torch.cuda.is_available():
            device = torch.device("cuda")  # NVIDIA GPU
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = torch.device("mps")  # Apple Silicon (Metal)
        else:
            device = torch.device("cpu")  # Fallback

        # 加载并预处理图像
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
        ])
        img = Image.open(file).convert('RGB')
        img = transform(img)
        img = Variable(img.unsqueeze(0)).to(device)

        # 加载预训练模型的权重和偏差
        vgg16 = models.vgg16_bn()
        vgg16.classifier[-1] = nn.Linear(4096, 4)  # 根据你的具体问题调整输出层
        vgg16.load_state_dict(torch.load(model_path))
        vgg16.eval()

        # 将 VGG16 模型移动到相同的设备上
        vgg16 = vgg16.to(device)

        # 使用新模型进行预测
        with torch.no_grad():
            preds_new_model = vgg16(img)

        # 处理结果
        _, predicted_class_new_model = torch.max(preds_new_model, 1)
        result_new_model = int(predicted_class_new_model)

        # 返回 JSON 响应
        category_mapping = ['脉络膜新生血管 [CNV]', '糖尿病性黄斑水肿 [DME]', '玻璃膜疣 [DRUSEN]', '无异常 [NORMAL]']
        print("Predicted Result (New Model):", result_new_model)
        print("Predicted Category (New Model):", category_mapping[result_new_model])

        # 获取当前登录用户的手机号
        mobile = session.get('mobile')
        if mobile:
            # 将预测结果存入数据库
            result_string = category_mapping[result_new_model]
            db.insert_result(result_string)  # 假设存在一个方法用于将结果插入到特定用户记录中

        return jsonify(result_new_model=result_new_model, vgg16=category_mapping[result_new_model])

    return jsonify(error="Unexpected error")


@app.route('/save_result', methods=['POST'])
def save_result():
    data = request.get_json()
    result = data.get('result')  # 获取预测结果
    if result:
        # 将预测结果插入到数据库中的 result 字段
        db.insert_result(result)
        return jsonify(message="预测结果已保存到数据库.")
    else:
        return jsonify(error="无法保存预测结果.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg'}

def open_browser():
    # 打开默认浏览器并访问http://127.0.0.1:5000/
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    threading.Timer(1, open_browser).start()  # 等待1秒后打开浏览器
    # 使用gevent启动应用程序
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()