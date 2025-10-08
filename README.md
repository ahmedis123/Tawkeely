
```markdown
# منصة التوكيلات الإلكترونية | Tawkeel Platform

<p align="center">
  <img src="https://raw.githubusercontent.com/m-a-bey/Tawkeel-Platform/main/assets/logo.png" alt="شعار منصة التوكيلات" width="150"/>
</p>

<p align="center">
  <strong>وكيلك الرقمي: منصة ويب متكاملة لإنشاء وإدارة التوكيلات الإلكترونية بشكل آمن وسريع.</strong>
  <br><br>
  <a href="#-المميزات-الرئيسية">المميزات</a> •
  <a href="#-التقنيات-المستخدمة">التقنيات</a> •
  <a href="#-كيفية-التشغيل-المحلي">التشغيل المحلي</a> •
  <a href="#-هيكل-المشروع">هيكل المشروع</a> •
  <a href="#-المساهمة">المساهمة</a>
</p>

---

## 📜 نظرة عامة

**Tawkeel Platform** هو مشروع مفتوح المصدر يهدف إلى تبسيط الإجراءات الرسمية المتعلقة بالتوكيلات من خلال توفير حل رقمي متكامل. تم بناء المنصة باستخدام Python و Flask، وهي تقدم واجهة مستخدم سهلة باللغة العربية تسمح للمستخدمين بإنشاء توكيلات مخصصة، وتقديمها للمراجعة والتوثيق من قبل موثق معتمد، ومن ثم تحميلها كملفات PDF رسمية ومحمية برمز تحقق (QR Code).

## ✨ المميزات الرئيسية

-   **تصميم عصري ومتجاوب**: واجهة مستخدم حديثة تعمل بكفاءة على جميع الأجهزة (كمبيوتر، تابلت، جوال).
-   **قوالب توكيلات متنوعة**: 8 أنواع مختلفة من التوكيلات الجاهزة (بيع سيارة، إدارة عقار، تمثيل قانوني، وغيرها).
-   **نظام أدوار متكامل**:
    -   **المستخدم (User):** إنشاء التوكيلات وتتبع حالتها.
    -   **الموثق (Notary):** مراجعة التوكيلات، والموافقة عليها أو رفضها.
    -   **المدير (Admin):** إدارة المستخدمين والنظام بشكل عام.
-   **إنشاء ملفات PDF ديناميكيًا**: توليد ملفات PDF باللغة العربية بتنسيق احترافي ومنظم للتوكيلات المعتمدة.
-   **التحقق عبر رمز QR**: كل توكيل معتمد يحتوي على رمز QR فريد يمكن مسحه للتحقق من صحة المستند وحالته عبر الإنترنت.
-   **نظام إشعارات**: إرسال إشعارات تلقائية للمستخدمين عند تغيير حالة توكيلاتهم (إنشاء، موافقة، رفض).
-   **لوحات تحكم مخصصة**: لكل دور (مستخدم، موثق، مدير) لوحة تحكم خاصة به تعرض الإحصائيات والإجراءات المتعلقة به.
-   **أمان**: حماية كلمات المرور (Hashing)، وتأمين جلسات المستخدمين.

## 🚀 التقنيات المستخدمة

-   **الواجهة الخلفية (Backend):**
    -   [Python 3](https://www.python.org/)
    -   [Flask](https://flask.palletsprojects.com/): إطار عمل الويب.
    -   [Flask-Login](https://flask-login.readthedocs.io/): لإدارة جلسات المستخدمين.
    -   [Werkzeug](https://werkzeug.palletsprojects.com/): لتأمين كلمات المرور.
-   **إنشاء PDF و QR Code:**
    -   [ReportLab](https://www.reportlab.com/): لإنشاء ملفات PDF.
    -   [Pillow (PIL Fork)](https://python-pillow.org/): لمعالجة الصور.
    -   [qrcode](https://github.com/lincolnloop/python-qrcode): لإنشاء رموز QR.
    -   [arabic-reshaper](https://github.com/mpc-jov/python-arabic-reshaper) & [python-bidi](https://github.com/MeirKriheli/python-bidi): لدعم اللغة العربية في ملفات PDF.
-   **الواجهة الأمامية (Frontend):**
    -   HTML5
    -   [Bootstrap 5](https://getbootstrap.com/): إطار عمل CSS.
    -   [Font Awesome](https://fontawesome.com/): للأيقونات.
    -   JavaScript (لتحسين تجربة المستخدم).

## 🛠️ كيفية التشغيل المحلي

اتبع الخطوات التالية لتشغيل المشروع على جهازك المحلي.

**1. المتطلبات المسبقة:**
-   تأكد من تثبيت [Python 3.8](https://www.python.org/downloads/) أو أحدث.
-   تأكد من تثبيت [Git](https://git-scm.com/).

**2. استنساخ المستودع:**
```bash
git clone https://github.com/ahmedis123/Tawkeel-Platform.git
cd Tawkeel-Platform
```

**3. إنشاء بيئة افتراضية (اختياري ولكن موصى به):**
```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**4. تثبيت المكتبات المطلوبة:**
المشروع يستخدم مكتبات متعددة. قم بتثبيتها جميعًا باستخدام الأمر التالي:
```bash
pip install Flask Flask-Login Werkzeug qrcode Pillow reportlab arabic-reshaper python-bidi
```

**5. تشغيل التطبيق:**
```bash
python unified.py
```
سيتم تشغيل التطبيق على العنوان `http://127.0.0.1:5000`.

**6. حسابات افتراضية للوصول:**
-   **المدير:**
    -   اسم المستخدم: `admin`
    -   كلمة المرور: `admin123`
-   **الموثق:**
    -   اسم المستخدم: `notary1`
    -   كلمة المرور: `notary123`
-   **المستخدم:**
    -   اسم المستخدم: `user`
    -   كلمة المرور: `user123`

## 📂 هيكل المشروع

```
Tawkeel-Platform/
│
├── unified.py              # الملف الرئيسي للتطبيق (Flask App)
├── Amiri-Regular.ttf       # ملف الخط العربي المستخدم في PDF
├── README.md               # هذا الملف
├── .gitignore              # ملف لتجاهل الملفات غير المرغوب فيها
└── assets/                 # (مجلد مقترح) لوضع الصور والشعارات
    └── logo.png
```

## 🤝 المساهمة

المساهمات مرحب بها لجعل هذا المشروع أفضل! إذا كانت لديك فكرة لميزة جديدة أو وجدت خطأ، لا تتردد في فتح [Issue](https://github.com/ahmedis123/Tawkeel-Platform/issues) لمناقشته.

للمساهمة في الكود:
1.  قم بعمل Fork للمستودع.
2.  أنشئ فرعًا جديدًا لميزتك (`git checkout -b feature/AmazingFeature`).
3.  قم بعمل Commit لتغييراتك (`git commit -m 'Add some AmazingFeature'`).
4.  قم برفع التغييرات إلى الفرع (`git push origin feature/AmazingFeature`).
5.  افتح Pull Request.

---
صُنع بـ ❤️ في السودان.
```

### ملاحظات هامة

1.  **الشعار (Logo):**
    *   لقد أضفت رابطًا لصورة شعار في بداية الملف. ستحتاج إلى إنشاء مجلد باسم `assets` في مشروعك، ووضع صورة شعار باسم `logo.png` بداخله، ثم رفعها إلى GitHub لكي تظهر. إذا لم ترد إضافة شعار، يمكنك حذف هذا الجزء.
2.  **اسم المستخدم:**
    *   لا تنسَ استبدال `your-username` في جميع الروابط باسم المستخدم الخاص بك على GitHub.
3.  **ملف `requirements.txt`:**
    *   لجعل مشروعك أكثر احترافية، يمكنك إنشاء ملف `requirements.txt` يحتوي على جميع المكتبات. يمكنك إنشاؤه بالأمر التالي (بعد تثبيت المكتبات):
        ```bash
        pip freeze > requirements.txt
        ```
    *   بعدها، يمكن لأي شخص تثبيت كل شيء بأمر واحد: `pip install -r requirements.txt`. لقد أضفت الأمر القديم في ملف `README` ليكون أبسط للمبتدئين.
