import os
import base64
import uuid
from io import BytesIO
from datetime import datetime, timedelta
import random
import string
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template_string, request, make_response, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
import arabic_reshaper
from bidi.algorithm import get_display



# مجلد البرنامج الحالي
base_path = os.path.dirname(__file__)

# تسجيل الخطوط
pdfmetrics.registerFont(TTFont('Amiri-Regular', os.path.join(base_path, 'Amiri-Regular.ttf')))
pdfmetrics.registerFont(TTFont('Amiri-Bold', os.path.join(base_path, 'Amiri-Bold.ttf')))
pdfmetrics.registerFont(TTFont('Amiri-Italic', os.path.join(base_path, 'Amiri-Italic.ttf')))
pdfmetrics.registerFont(TTFont('Amiri-BoldItalic', os.path.join(base_path, 'Amiri-BoldItalic.ttf')))


DB = {
    "tawkeels": {},
    "templates": {},
    "users": {},
    "settings": {
        "app_name": "منصة التوكيلات الإلكترونية",
        "company_name": "شركة التوكيلات الإلكترونية المحدودة"
    }
}

# =============================================================================
# تطبيق فلاسك والإعدادات
# =============================================================================

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-' + str(uuid.uuid4())),
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'pdf'},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

# إنشاء مجلد التحميلات إذا لم يكن موجوداً
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# إعدادات تسجيل الدخول
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "warning"

# =============================================================================
# *** تعديل: تسجيل الخط العربي ***
# =============================================================================
# تأكد من أن ملف الخط 'Amiri-Regular.ttf' موجود في نفس مجلد هذا الملف
try:
    pdfmetrics.registerFont(TTFont('Arabic-Font', 'Amiri-Regular.ttf'))
    print("تم تسجيل الخط العربي بنجاح لملفات PDF.")
except Exception as e:
    print(f"خطأ في تسجيل الخط العربي: {e}. تأكد من وجود ملف 'Amiri-Regular.ttf'.")


# =============================================================================
# قاعدة البيانات (محاكاة باستخدام القواميس)
# =============================================================================

DB = {
    "users": {},
    "tawkeels": {},
    "templates": {
        "cert_pickup": {
            "id": "cert_pickup",
            "title": "توكيل استلام شهادات جامعية",
            "description": "تفويض لاستلام الشهادات والمستندات من الجامعات",
            "icon": "fa-graduation-cap",
            "category": "تعليمي",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في استلام شهادتي الجامعية وكافة المستندات المتعلقة بها من جامعة [اسم الجامعة]، والتوقيع على كافة الأوراق والمستندات المطلوبة لذلك."
        },
        "car_sale": {
            "id": "car_sale", 
            "title": "توكيل بيع سيارة",
            "description": "تفويض لبيع المركبات وتوقيع عقود البيع",
            "icon": "fa-car",
            "category": "مركبات",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في بيع سيارتي نوع [نوع السيارة] موديل [الموديل] رقم لوحة [رقم اللوحة]، وقبض الثمن والتوقيع على عقد البيع النهائي واستلام كافة المستندات."
        },
        "property_management": {
            "id": "property_management",
            "title": "توكيل إدارة عقار",
            "description": "تفويض لإدارة الأملاك والعقارات وتلقي الإيجارات",
            "icon": "fa-building",
            "category": "عقارات",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في إدارة عقاري الكائن في [عنوان العقار]، وتلقي الإيجارات وإبرام عقود الإيجار وإجراء الصيانة اللازمة والتصرف في كل ما يلزم لإدارة العقار."
        },
        "legal_representation": {
            "id": "legal_representation",
            "title": "توكيل تمثيل قانوني",
            "description": "تفويض للمرافعة أمام المحاكم والجهات القضائية",
            "icon": "fa-gavel",
            "category": "قانوني",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في المرافعة أمام المحاكم والنيابات وكافة الجهات القضائية في الدعوى المقامة من/على [اسم الطرف الآخر]، وتقديم المستندات والطلبات وكل ما يلزم لإتمام الإجراءات القانونية."
        },
        "bank_transactions": {
            "id": "bank_transactions",
            "title": "توكيل معاملات بنكية",
            "description": "تفويض لإجراء العمليات البنكية المختلفة",
            "icon": "fa-university",
            "category": "بنكي",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في إجراء كافة المعاملات البنكية على حسابي رقم [رقم الحساب] في بنك [اسم البنك]، بما في ذلك السحب والإيداع والتحويل وإصدار الشيكات وكافة العمليات المتعلقة بالحساب."
        },
        "medical_decisions": {
            "id": "medical_decisions",
            "title": "توكيل قرارات طبية",
            "description": "تفويض لاتخاذ القرارات الطبية في حالات الطوارئ",
            "icon": "fa-heartbeat",
            "category": "طبي",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في اتخاذ القرارات الطبية نيابة عني في حال تعذر علي ذلك، والموافقة على الإجراءات والعمليات الطبية وتوقيع كافة المستندات المتعلقة بالعلاج."
        },
        "business_representation": {
            "id": "business_representation",
            "title": "توكيل تمثيل تجاري",
            "description": "تفويض لإدارة الأعمال التجارية والتوقيع على العقود",
            "icon": "fa-briefcase",
            "category": "تجاري",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في إدارة أعمالي التجارية والتفاوض على العقود والاتفاقيات التجارية والتوقيع عليها ومتابعة كافة الشؤون الإدارية والمالية."
        },
        "custom": {
            "id": "custom",
            "title": "توكيل خاص",
            "description": "توكيل مخصص حسب الاحتياجات الخاصة",
            "icon": "fa-file-signature",
            "category": "خاص",
            "template_text": "أنا الموكل أدناه أفوض الوكيل في [الغرض المخصص] وفق الشروط والإجراءات المتفق عليها."
        }
    },
    "notifications": {},
    "settings": {
        "app_name": "منصة التوكيلات الإلكترونية",
        "support_email": "ahmed.dawoud.mohamed@gmail.com",
        "support_phone": "+249116984204",
        "company_name": "شركة التوكيلات الإلكترونية المحدودة"
    }
}

# عدادات لتوليد المعرفات
COUNTERS = {
    'user': 1000,
    'tawkeel': 1000,
    'notification': 1000
}

# =============================================================================
# نماذج البيانات
# =============================================================================

class User(UserMixin):
    def __init__(self, id, username, email, password, first_name, last_name, 
                 phone=None, national_id=None, role='user', active=True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.national_id = national_id
        self.role = role
        self._active = active
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @property
    def is_active(self):
        return self._active
    
    def set_active(self, active):
        self._active = active
        self.updated_at = datetime.now()
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'phone': self.phone,
            'active': self._active,
            'created_at': self.created_at
        }
    
    @staticmethod
    def get(user_id):
        return DB["users"].get(user_id)

# =============================================================================
# وظائف مساعدة
# =============================================================================

def generate_id(entity_type):
    COUNTERS[entity_type] += 1
    return str(COUNTERS[entity_type])

def generate_reference_number():
    date_str = datetime.now().strftime('%Y-%m-%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"TKW-{date_str}-{random_str}"

def generate_qr_code(data, size=120):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        if size != 120:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def send_notification(user_id, title, message, notification_type='info', link=None):
    notification_id = generate_id('notification')
    DB["notifications"][notification_id] = {
        'id': notification_id,
        'user_id': user_id,
        'title': title,
        'message': message,
        'type': notification_type,
        'link': link,
        'is_read': False,
        'created_at': datetime.now()
    }
    return notification_id

def get_user_stats(user_id):
    user_tawkeels = [t for t in DB["tawkeels"].values() if t['user_id'] == user_id]
    
    return {
        'total': len(user_tawkeels),
        'pending': len([t for t in user_tawkeels if t['status'] == 'pending']),
        'approved': len([t for t in user_tawkeels if t['status'] == 'approved']),
        'rejected': len([t for t in user_tawkeels if t['status'] == 'rejected']),
        'expired': len([t for t in user_tawkeels if t['status'] == 'expired'])
    }

def get_notary_stats():
    all_tawkeels = DB["tawkeels"].values()
    today = datetime.now().date()
    
    return {
        'total': len(all_tawkeels),
        'pending': len([t for t in all_tawkeels if t['status'] == 'pending']),
        'approved': len([t for t in all_tawkeels if t['status'] == 'approved']),
        'rejected': len([t for t in all_tawkeels if t['status'] == 'rejected']),
        'today_pending': len([t for t in all_tawkeels if t['status'] == 'pending' and t['created_at'].date() == today]),
        'today_approved': len([t for t in all_tawkeels if t['status'] == 'approved' and t.get('approved_at') and t['approved_at'].date() == today]),
        'total_users': len([u for u in DB["users"].values() if u.role == 'user'])
    }

def arabic_text(text):
    """تحويل النص العربي للتنسيق الصحيح في PDF"""
    try:
        # التأكد من أن المدخل نصي
        if not isinstance(text, str):
            text = str(text)
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"Error in arabic_text function: {e}")
        return text

def generate_pdf(tawkeel_id):
    """
    إنشاء ملف PDF لتوكيل إلكتروني بالعربية بتصميم رسمي واحترافي.
    - يدعم النصوص العربية بشكل كامل (الاتجاه، الربط، التشكيل)
    - يعرض البيانات بترتيب منطقي من اليمين لليسار
    - يمنع تكرار أو انعكاس الجمل
    - يدمج QRCode للتحقق من صحة المستند
    """

    from reportlab.platypus import Image

    try:
        if tawkeel_id not in DB["tawkeels"]:
            return None

        tawkeel = DB["tawkeels"][tawkeel_id]
        template = DB["templates"][tawkeel['template_id']]

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm
        )

        # أنماط النصوص
        style_regular = ParagraphStyle(name='Arabic-Regular', fontName='Amiri-Regular', fontSize=11, alignment=2, leading=16)
        style_bold = ParagraphStyle(name='Arabic-Bold', fontName='Amiri-Bold', fontSize=11, alignment=2, leading=16)
        style_title_bold = ParagraphStyle(name='Arabic-Title-Bold', fontName='Amiri-Bold', fontSize=16, alignment=1, spaceAfter=10)
        style_heading_bold = ParagraphStyle(
            name='Arabic-Heading-Bold',
            fontName='Amiri-Bold',
            fontSize=13,
            alignment=2,
            spaceAfter=5,
            spaceBefore=8,
            borderBottomWidth=0.5,
            borderBottomColor=colors.HexColor('#2980b9'),
            paddingBottom=2
        )
        style_left = ParagraphStyle(name='Left-Normal', fontName='Amiri-Regular', fontSize=11, alignment=0)

        story = []

        # العنوان الرئيسي
        title_text = arabic_text(template['title'])
        story.append(Paragraph(title_text, style_title_bold))
        story.append(Spacer(1, 5 * mm))

        # --- معلومات التوكيل ---
        story.append(Paragraph(arabic_text("معلومات التوكيل"), style_heading_bold))
        info_data = [
            [Paragraph(tawkeel['reference_number'], style_left), Paragraph(arabic_text("رقم المرجع:"), style_regular)],
            [Paragraph(tawkeel['created_at'].strftime('%Y-%m-%d'), style_left), Paragraph(arabic_text("تاريخ الإنشاء:"), style_regular)],
            [Paragraph(arabic_text("تمت الموافقة"), style_regular), Paragraph(arabic_text("الحالة:"), style_regular)],
            [Paragraph(tawkeel['effective_date'].strftime('%Y-%m-%d'), style_left), Paragraph(arabic_text("تاريخ السريان:"), style_regular)],
            [Paragraph(tawkeel['expiration_date'].strftime('%Y-%m-%d'), style_left), Paragraph(arabic_text("تاريخ الانتهاء:"), style_regular)],
        ]
        info_table = Table(info_data, colWidths=[125 * mm, 50 * mm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f8f9fa')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)

        # --- أطراف التوكيل ---
        story.append(Paragraph(arabic_text("أطراف التوكيل"), style_heading_bold))
        party_data = [
            [Paragraph(arabic_text(tawkeel['principal_name']), style_regular), Paragraph(arabic_text("الاسم الكامل (الموكل):"), style_bold)],
            [Paragraph(tawkeel['principal_national_id'], style_left), Paragraph(arabic_text("رقم الهوية (الموكل):"), style_bold)],
            [Paragraph(arabic_text(tawkeel['agent_name']), style_regular), Paragraph(arabic_text("الاسم الكامل (الوكيل):"), style_bold)],
            [Paragraph(tawkeel['agent_national_id'], style_left), Paragraph(arabic_text("رقم الهوية (الوكيل):"), style_bold)],
        ]
        party_table = Table(party_data, colWidths=[125 * mm, 50 * mm])
        party_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fefefe')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(party_table)

        # --- الغرض من التوكيل ---
        story.append(Paragraph(arabic_text("الغرض من التوكيل"), style_heading_bold))

        purpose_text = tawkeel['purpose'].strip()
        story.append(Paragraph(arabic_text(purpose_text), style_regular))
        story.append(Spacer(1, 2 * mm))

        # إضافة جملة التفويض فقط إذا لم تكن موجودة
        if "أفوض الوكيل" not in purpose_text and "أنا الموكل" not in purpose_text:
            delegation_text = arabic_text("أنا الموكل أدناه أفوض الوكيل في تنفيذ ما ورد أعلاه وفقًا لما تم الاتفاق عليه.")
            story.append(Paragraph(delegation_text, style_regular))

        # --- التوقيعات ---
        story.append(Spacer(1, 10 * mm))
        approved_by_user = DB['users'].get(tawkeel.get('approved_by'))
        notary_name = approved_by_user.get_full_name() if approved_by_user else 'الموثق المعتمد'

        signatures_data = [
            [Paragraph(arabic_text("توقيع الموثق"), style_bold), Paragraph(arabic_text("توقيع الموكل"), style_bold)],
            [Spacer(1, 12 * mm), Spacer(1, 12 * mm)],
            [Paragraph(arabic_text(f"الاسم: {notary_name}"), style_regular),
             Paragraph(arabic_text(f"الاسم: {tawkeel['principal_name']}"), style_regular)],
            [Paragraph(arabic_text(f"التاريخ: {tawkeel.get('approved_at', datetime.now()).strftime('%Y-%m-%d')}"), style_regular), '']
        ]
        signatures_table = Table(signatures_data, colWidths=[87 * mm, 87 * mm])
        signatures_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 1), (0, 1), 1, colors.black),
            ('LINEABOVE', (1, 1), (1, 1), 1, colors.black),
        ]))
        story.append(signatures_table)

        # --- QR Code ---
        qr_url = url_for('verify_tawkeel', tawkeel_id=tawkeel_id, _external=True)
        qr_code_img = generate_qr_code(qr_url, size=200)
        if qr_code_img:
            qr_bytes = base64.b64decode(qr_code_img)
            qr_stream = BytesIO(qr_bytes)
            qr_img_obj = Image(qr_stream, width=25 * mm, height=25 * mm)
            qr_text = Paragraph(arabic_text("امسح الرمز للتحقق من صحة التوكيل"),
                                ParagraphStyle(name='QRText', fontName='Amiri-Regular', fontSize=9, alignment=1))
            qr_table = Table([[qr_img_obj, qr_text]], colWidths=[30 * mm, 140 * mm], rowHeights=28 * mm)
            qr_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER')
            ]))
            story.append(Spacer(1, 8 * mm))
            story.append(qr_table)

        # --- التذييل ---
        def footer_canvas(canvas, doc):
            canvas.saveState()
            canvas.setFont('Amiri-Regular', 8)
            footer_text = arabic_text(
                f"هذا التوكيل تم إنشاؤه إلكترونيًّا عبر {DB['settings']['app_name']} - {DB['settings']['company_name']}"
            )
            canvas.drawCentredString(A4[0] / 2, 12 * mm, footer_text)
            canvas.restoreState()

        # إنشاء المستند النهائي
        doc.build(story, onFirstPage=footer_canvas, onLaterPages=footer_canvas)
        buffer.seek(0)
        return buffer

    except Exception as e:
        import traceback
        print(f"Error generating PDF: {e}")
        traceback.print_exc()
        return None

def init_default_data():
    if not any(user.username == 'admin' for user in DB["users"].values()):
        admin_user = User(
            id=generate_id('user'),
            username='admin',
            email='admin@tawkeel.sd',
            password='admin123',
            first_name='مدير',
            last_name='النظام',
            role='admin',
            national_id='0000000000',
            active=True
        )
        DB["users"][admin_user.id] = admin_user
        print(f"تم إنشاء المستخدم الإداري: admin / admin123")
    
    if not any(user.username == 'notary1' for user in DB["users"].values()):
        notary_user = User(
            id=generate_id('user'),
            username='notary1',
            email='notary1@tawkeel.sd',
            password='notary123',
            first_name='موثق',
            last_name='معتمد',
            role='notary',
            national_id='1111111111',
            active=True
        )
        DB["users"][notary_user.id] = notary_user
        print(f"تم إنشاء المستخدم الموثق: notary1 / notary123")
    
    if not any(user.username == 'user' for user in DB["users"].values()):
        normal_user = User(
            id=generate_id('user'),
            username='user',
            email='user@tawkeel.sd',
            password='user123',
            first_name='مستخدم',
            last_name='عادي',
            role='user',
            national_id='2222222222',
            active=True
        )
        DB["users"][normal_user.id] = normal_user
        print(f"تم إنشاء المستخدم العادي: user / user123")

# =============================================================================
# إعدادات تسجيل الدخول
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# =============================================================================
# نظام القوالب
# =============================================================================

def render_full_template(template_content, **context):
    base_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/animate.css@4.1.1/animate.min.css" rel="stylesheet">
    
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --light-bg: #f8f9fa;
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --shadow-light: 0 2px 15px rgba(0,0,0,0.08);
            --shadow-medium: 0 5px 25px rgba(0,0,0,0.15);
            --shadow-heavy: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        * {
            font-family: 'Tajawal', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding-top: 80px;
            line-height: 1.7;
        }
        
        .navbar {
            background: var(--gradient-primary) !important;
            box-shadow: var(--shadow-medium);
            backdrop-filter: blur(10px);
            padding: 0.8rem 0;
        }
        
        .navbar-brand {
            font-weight: 800;
            font-size: 1.5rem;
            background: linear-gradient(45deg, #fff, #e3f2fd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-link {
            font-weight: 500;
            margin: 0 0.3rem;
            border-radius: 25px;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .nav-link:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-2px);
        }
        
        .nav-link.active {
            background: rgba(255,255,255,0.2);
            font-weight: 700;
        }
        
        .hero-section {
            background: var(--gradient-primary), 
                       url('https://images.unsplash.com/photo-1450101499163-c8848c66ca85?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80');
            background-size: cover;
            background-position: center;
            border-radius: 20px;
            margin: 2rem 0;
            padding: 5rem 2rem;
            color: white;
            text-align: center;
            box-shadow: var(--shadow-heavy);
            position: relative;
            overflow: hidden;
        }
        
                .hero-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
        }
        
        .hero-section > * {
            position: relative;
            z-index: 2;
        }
        
        .feature-icon {
            font-size: 3rem;
            background: var(--gradient-secondary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1.5rem;
            transition: transform 0.3s ease;
        }
        
        .feature-card:hover .feature-icon {
            transform: scale(1.1) rotate(5deg);
        }
        
        .stat-card {
            border-radius: 15px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            border: none;
            box-shadow: var(--shadow-light);
            overflow: hidden;
            position: relative;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }
        
        .stat-card:hover {
            transform: translateY(-10px) scale(1.02);
            box-shadow: var(--shadow-heavy);
        }
        
        .stat-number {
            font-size: 2.8rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .tawkeel-card {
            transition: all 0.3s ease;
            border: none;
            box-shadow: var(--shadow-light);
            border-radius: 15px;
            overflow: hidden;
        }
        
        .tawkeel-card:hover {
            transform: translateY(-8px);
            box-shadow: var(--shadow-medium);
        }
        
        .tawkeel-card .card-header {
            background: var(--gradient-primary);
            color: white;
            font-weight: 700;
            border: none;
            padding: 1.2rem;
        }
        
        .step-number {
            width: 70px;
            height: 70px;
            background: var(--gradient-success);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.5rem;
            margin: 0 auto 1.5rem;
            box-shadow: var(--shadow-medium);
            transition: transform 0.3s ease;
        }
        
        .step-number:hover {
            transform: scale(1.1) rotate(360deg);
        }
        
        .notification-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
        }
        
        .btn {
            border-radius: 25px;
            font-weight: 600;
            padding: 0.75rem 2rem;
            transition: all 0.3s ease;
            border: none;
            position: relative;
            overflow: hidden;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn-primary {
            background: var(--gradient-primary);
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.6);
        }
        
        .btn-success {
            background: var(--gradient-success);
            box-shadow: 0 4px 15px rgba(39, 174, 96, 0.4);
        }
        
        .btn-success:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(39, 174, 96, 0.6);
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: var(--shadow-light);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            box-shadow: var(--shadow-medium);
        }
        
        .card-header {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-bottom: 1px solid rgba(0,0,0,0.1);
            font-weight: 700;
            padding: 1.2rem 1.5rem;
        }
        
        .table th {
            background: var(--gradient-primary);
            color: white;
            font-weight: 600;
            border: none;
            padding: 1rem;
        }
        
        .table td {
            padding: 1rem;
            vertical-align: middle;
            border-color: #f1f3f4;
        }
        
        .table-hover tbody tr:hover {
            background-color: rgba(52, 152, 219, 0.05);
            transform: scale(1.01);
            transition: all 0.2s ease;
        }
        
        .badge {
            border-radius: 20px;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }
        
        .form-control, .form-select {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }
        
        .form-control:focus, .form-select:focus {
            border-color: var(--secondary-color);
            box-shadow: 0 0 0 0.2rem rgba(52, 152, 219, 0.25);
            transform: translateY(-2px);
        }
        
        footer {
            background: var(--gradient-primary);
            color: white;
            margin-top: 4rem;
            padding: 3rem 0 1rem;
        }
        
        footer a {
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            transition: color 0.3s ease;
        }
        
        footer a:hover {
            color: white;
            text-decoration: underline;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--secondary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .fade-in {
            animation: fadeIn 0.8s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .gradient-text {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        
        .glass-effect {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        @media (max-width: 768px) {
            body { padding-top: 70px; }
            .hero-section { padding: 3rem 1rem; margin: 1rem 0; }
            .stat-number { font-size: 2rem; }
            .btn { padding: 0.6rem 1.5rem; }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-file-contract me-2"></i>
                {{ settings.app_name }}
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if current_user.is_authenticated %}
                        <li class="nav-item">
                            <a class="nav-link {{ 'active' if request.endpoint == 'dashboard' }}" href="{{ url_for('dashboard') }}">
                                <i class="fas fa-tachometer-alt me-1"></i> لوحة التحكم
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link {{ 'active' if request.endpoint == 'tawkeel_list' }}" href="{{ url_for('tawkeel_list') }}">
                                <i class="fas fa-list me-1"></i> التوكيلات
                            </a>
                        </li>
                        {# *** تعديل: إخفاء زر إنشاء توكيل من الأدمن *** #}
                        {% if current_user.role != 'admin' %}
                        <li class="nav-item">
                            <a class="nav-link {{ 'active' if request.endpoint == 'create_tawkeel' }}" href="{{ url_for('create_tawkeel') }}">
                                <i class="fas fa-plus-circle me-1"></i> إنشاء توكيل
                            </a>
                        </li>
                        {% endif %}
                        {% if current_user.role == 'admin' %}
                        <li class="nav-item">
                            <a class="nav-link {{ 'active' if request.endpoint == 'admin_dashboard' }}" href="{{ url_for('admin_dashboard') }}">
                                <i class="fas fa-cogs me-1"></i> لوحة الإدارة
                            </a>
                        </li>
                        {% endif %}
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="#services">
                                <i class="fas fa-concierge-bell me-1"></i> الخدمات
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#how-it-works">
                                <i class="fas fa-info-circle me-1"></i> كيفية العمل
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#features">
                                <i class="fas fa-star me-1"></i> المميزات
                            </a>
                        </li>
                    {% endif %}
                </ul>
                
                <ul class="navbar-nav">
                    {% if current_user.is_authenticated %}
                        {% set unread_notifications = [] %}
                        {% for notification in notifications.values() %}
                            {% if notification.user_id == current_user.id and not notification.is_read %}
                                {% set _ = unread_notifications.append(notification) %}
                            {% endif %}
                        {% endfor %}
                        
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle position-relative" href="#" id="notificationsDropdown" role="button" data-bs-toggle="dropdown">
                                <i class="fas fa-bell"></i>
                                {% if unread_notifications %}
                                    <span class="badge bg-danger notification-badge">{{ unread_notifications|length }}</span>
                                {% endif %}
                            </a>
                            <div class="dropdown-menu dropdown-menu-end">
                                <h6 class="dropdown-header">الإشعارات</h6>
                                {% if unread_notifications %}
                                    {% for notification in unread_notifications[:5] %}
                                        <a class="dropdown-item" href="{{ notification.link or '#' }}">
                                            <div class="fw-bold">{{ notification.title }}</div>
                                            <small>{{ notification.message[:50] }}{% if notification.message|length > 50 %}...{% endif %}</small>
                                        </a>
                                    {% endfor %}
                                    <div class="dropdown-divider"></div>
                                    <a class="dropdown-item text-center" href="{{ url_for('notifications_page') }}">عرض جميع الإشعارات</a>
                                {% else %}
                                    <span class="dropdown-item-text">لا توجد إشعارات جديدة</span>
                                {% endif %}
                            </div>
                        </li>
                        
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                                <i class="fas fa-user-circle me-1"></i> {{ current_user.get_full_name() }}
                            </a>
                            <div class="dropdown-menu dropdown-menu-end">
                                <a class="dropdown-item" href="{{ url_for('profile') }}">
                                    <i class="fas fa-user me-2"></i>الملف الشخصي
                                </a>
                                {% if current_user.role in ['notary', 'admin'] %}
                                    <a class="dropdown-item" href="{{ url_for('notary_dashboard') }}">
                                        <i class="fas fa-gavel me-2"></i>لوحة الموثق
                                    </a>
                                {% endif %}
                                <div class="dropdown-divider"></div>
                                <a class="dropdown-item" href="{{ url_for('logout') }}">
                                    <i class="fas fa-sign-out-alt me-2"></i>تسجيل الخروج
                                </a>
                            </div>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('login') }}">
                                <i class="fas fa-sign-in-alt me-1"></i> تسجيل الدخول
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="btn btn-outline-light ms-2" href="{{ url_for('register') }}">
                                <i class="fas fa-user-plus me-1"></i> إنشاء حساب
                            </a>
                        </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show mt-3 animate__animated animate__fadeIn" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {{ content|safe }}
    </main>

    <footer class="bg-dark text-light py-4 mt-5">
        <div class="container">
            <div class="row">
                <div class="col-md-4 mb-4">
                    <h5 class="gradient-text">{{ settings.app_name }}</h5>
                    <p class="mt-3">منصة متكاملة لإنشاء وإدارة التوكيلات الإلكترونية بشكل آمن وسهل</p>
                    <div class="social-links mt-3">
                        <a href="#" class="text-light me-3"><i class="fab fa-facebook fa-lg"></i></a>
                        <a href="#" class="text-light me-3"><i class="fab fa-twitter fa-lg"></i></a>
                        <a href="#" class="text-light me-3"><i class="fab fa-linkedin fa-lg"></i></a>
                        <a href="#" class="text-light"><i class="fab fa-instagram fa-lg"></i></a>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <h5>روابط سريعة</h5>
                    <ul class="list-unstyled">
                        <li class="mb-2"><a href="{{ url_for('index') }}" class="text-light">الرئيسية</a></li>
                        {% if current_user.is_authenticated %}
                            <li class="mb-2"><a href="{{ url_for('dashboard') }}" class="text-light">لوحة التحكم</a></li>
                            {% if current_user.role != 'admin' %}
                            <li class="mb-2"><a href="{{ url_for('create_tawkeel') }}" class="text-light">إنشاء توكيل</a></li>
                            {% endif %}
                        {% else %}
                            <li class="mb-2"><a href="{{ url_for('login') }}" class="text-light">تسجيل الدخول</a></li>
                            <li class="mb-2"><a href="{{ url_for('register') }}" class="text-light">إنشاء حساب</a></li>
                        {% endif %}
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>اتصل بنا</h5>
                    <p><i class="fas fa-envelope me-2"></i> {{ settings.support_email }}</p>
                    <p><i class="fas fa-phone me-2"></i> {{ settings.support_phone }}</p>
                    <p><i class="fas fa-map-marker-alt me-2"></i> السودان، الخرطوم</p>
                </div>
            </div>
            <hr class="my-4">
            <div class="text-center">
                <p>&copy; {{ now.year }} {{ settings.company_name }}. جميع الحقوق محفوظة.</p>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // إضافة تأثيرات للعناصر
            const cards = document.querySelectorAll('.card, .stat-card, .tawkeel-card');
            cards.forEach(card => {
                card.classList.add('animate__animated', 'animate__fadeInUp');
            });

            // إضافة تأثيرات للأزرار
            const buttons = document.querySelectorAll('.btn');
            buttons.forEach(btn => {
                btn.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-3px)';
                });
                btn.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });

            // منع إرسال النموذج المزدوج
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function() {
                    const submitBtn = this.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<span class="loading-spinner me-2"></span> جاري المعالجة...';
                    }
                });
            });

            // تأثير التمرير السلس
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        });
    </script>
</body>
</html>
    """
    
    full_template = base_template.replace("{{ content|safe }}", template_content)
    full_template = full_template.replace("{{ title }}", context.get('title', context['settings']['app_name']))
    
    return render_template_string(full_template, **context)

# =============================================================================
# المسارات الرئيسية
# =============================================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    home_content = """
    <div class="hero-section animate__animated animate__fadeIn">
        <h1 class="display-4 fw-bold mb-4">منصة التوكيلات الإلكترونية</h1>
        <p class="lead mb-4 fs-5">أنشئ توكيلاتك الرسمية إلكترونياً في دقائق، ووفر وقتك وجهدك مع منصتنا المتكاملة</p>
        {% if not current_user.is_authenticated %}
            <div class="mt-5">
                <a href="{{ url_for('register') }}" class="btn btn-light btn-lg px-5 me-3 shadow">
                    <i class="fas fa-rocket me-2"></i>ابدأ الآن
                </a>
                <a href="#services" class="btn btn-outline-light btn-lg px-5">
                    <i class="fas fa-play-circle me-2"></i>اعرف أكثر
                </a>
            </div>
        {% else %}
            <div class="mt-5">
                <a href="{{ url_for('create_tawkeel') }}" class="btn btn-light btn-lg px-5 me-3 shadow">
                    <i class="fas fa-plus-circle me-2"></i>إنشاء توكيل جديد
                </a>
                <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light btn-lg px-5">
                    <i class="fas fa-tachometer-alt me-2"></i>لوحة التحكم
                </a>
            </div>
        {% endif %}
    </div>

    <section id="features" class="py-5">
        <div class="container">
            <div class="row text-center mb-5">
                <div class="col-12">
                    <h2 class="gradient-text display-5 fw-bold mb-3">لماذا تختار منصتنا؟</h2>
                    <p class="lead text-muted">نقدم لك حلولاً متكاملة لتلبية جميع احتياجاتك في إنشاء التوكيلات</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100 text-center border-0">
                        <div class="card-body p-4">
                            <i class="fas fa-bolt feature-icon"></i>
                            <h5 class="card-title fw-bold">سريع وسهل</h5>
                            <p class="card-text text-muted">أنشئ توكيلك في دقائق معدودة بواجهة بسيطة وسهلة الاستخدام</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100 text-center border-0">
                        <div class="card-body p-4">
                            <i class="fas fa-shield-alt feature-icon"></i>
                            <h5 class="card-title fw-bold">آمن ومصدق</h5>
                            <p class="card-text text-muted">توكيلات معتمدة من موثقين معتمدين مع رموز تحقق إلكترونية</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100 text-center border-0">
                        <div class="card-body p-4">
                            <i class="fas fa-mobile-alt feature-icon"></i>
                            <h5 class="card-title fw-bold">متوفر دائماً</h5>
                            <p class="card-text text-muted">الوصول إلى منصتنا من أي جهاز وفي أي وقت يناسبك</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="services" class="py-5 bg-light">
        <div class="container">
            <h2 class="text-center mb-5 gradient-text display-5 fw-bold">خدماتنا المتكاملة</h2>
            <div class="row">
                {% for template in templates.values() %}
                <div class="col-lg-4 col-md-6 mb-4">
                    <div class="card h-100 tawkeel-card border-0">
                        <div class="card-body text-center p-4">
                            <i class="fas {{ template.icon }} feature-icon"></i>
                            <h5 class="card-title fw-bold">{{ template.title }}</h5>
                            <p class="card-text text-muted">{{ template.description }}</p>
                            {% if current_user.is_authenticated %}
                                {% if current_user.role != 'admin' %}
                                <a href="{{ url_for('create_tawkeel', template_id=template.id) }}" class="btn btn-primary mt-3">إنشاء توكيل</a>
                                {% endif %}
                            {% else %}
                                <a href="{{ url_for('login') }}" class="btn btn-outline-primary mt-3">تسجيل الدخول لإنشاء توكيل</a>
                            {% endif %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>

    <section id="how-it-works" class="py-5">
        <div class="container">
            <h2 class="text-center mb-5 gradient-text display-5 fw-bold">كيفية العمل في 3 خطوات</h2>
            <div class="row">
                <div class="col-md-4 text-center mb-4">
                    <div class="step-number">1</div>
                    <h4 class="fw-bold">إنشاء حساب</h4>
                    <p class="text-muted">سجل في المنصة وأنشئ حسابك الشخصي في دقائق معدودة</p>
                </div>
                <div class="col-md-4 text-center mb-4">
                    <div class="step-number">2</div>
                    <h4 class="fw-bold">إنشاء التوكيل</h4>
                    <p class="text-muted">اختر نوع التوكيل المناسب وأدخل المعلومات المطلوبة بسهولة</p>
                </div>
                <div class="col-md-4 text-center mb-4">
                    <div class="step-number">3</div>
                    <h4 class="fw-bold">التوثيق الإلكتروني</h4>
                    <p class="text-muted">يوثق الموثق التوكيل إلكترونياً ويصبح جاهزاً للاستخدام</p>
                </div>
            </div>
        </div>
    </section>

    <section class="py-5 bg-light">
        <div class="container text-center">
            <h2 class="mb-4 gradient-text display-5 fw-bold">جاهز للبدء؟</h2>
            <p class="lead mb-4 fs-5">انضم إلى الآلاف الذين يستخدمون منصتنا لإنشاء توكيلاتهم الإلكترونية بكل سهولة وأمان</p>
            {% if not current_user.is_authenticated %}
                <a href="{{ url_for('register') }}" class="btn btn-primary btn-lg px-5 py-3">
                    <i class="fas fa-user-plus me-2"></i>إنشاء حساب مجاني
                </a>
            {% else %}
                {% if current_user.role != 'admin' %}
                <a href="{{ url_for('create_tawkeel') }}" class="btn btn-primary btn-lg px-5 py-3">
                    <i class="fas fa-plus-circle me-2"></i>إنشاء توكيل جديد
                </a>
                {% endif %}
            {% endif %}
        </div>
    </section>
    """
    
    return render_full_template(
        home_content, 
        title=DB["settings"]["app_name"],
        settings=DB["settings"], 
        templates=DB["templates"], 
        notifications=DB["notifications"],
        now=datetime.utcnow()
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # *** تعديل: توجيه المستخدمين الحاليين إلى لوحات التحكم الصحيحة ***
        if current_user.role in ['admin', 'notary']:
            return redirect(url_for('notary_dashboard'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        user = next((u for u in DB["users"].values() if u.username == username), None)
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember_me)
            
            send_notification(
                user.id, 
                "تم تسجيل الدخول بنجاح", 
                f"مرحباً بعودتك {user.get_full_name()}! تم تسجيل الدخول إلى حسابك بنجاح.",
                'success'
            )
            
            flash('تم تسجيل الدخول بنجاح!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            # *** تعديل: توجيه المستخدمين الجدد إلى لوحات التحكم الصحيحة ***
            if user.role in ['admin', 'notary']:
                return redirect(url_for('notary_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    
    # ... باقي كود الدالة كما هو ...
    
    login_content = """
    <div class="row justify-content-center">
        <div class="col-md-6 col-lg-5">
            <div class="card shadow border-0 animate__animated animate__fadeIn">
                <div class="card-body p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-lock fa-3x gradient-text mb-3"></i>
                        <h2 class="card-title gradient-text">تسجيل الدخول</h2>
                        <p class="text-muted">ادخل بياناتك للوصول إلى حسابك</p>
                    </div>
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label fw-bold">اسم المستخدم</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border-end-0"><i class="fas fa-user"></i></span>
                                <input type="text" class="form-control border-start-0" id="username" name="username" required placeholder="ادخل اسم المستخدم">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label fw-bold">كلمة المرور</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border-end-0"><i class="fas fa-key"></i></span>
                                <input type="password" class="form-control border-start-0" id="password" name="password" required placeholder="ادخل كلمة المرور">
                            </div>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="remember_me" name="remember_me">
                            <label class="form-check-label" for="remember_me">تذكرني</label>
                        </div>
                        <button type="submit" class="btn btn-primary w-100 py-2 fw-bold">تسجيل الدخول</button>
                    </form>
                    <hr class="my-4">
                    <p class="text-center">ليس لديك حساب؟ <a href="{{ url_for('register') }}" class="text-decoration-none fw-bold">إنشاء حساب جديد</a></p>
                </div>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        login_content,
        title="تسجيل الدخول - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        now=datetime.utcnow()
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        national_id = request.form.get('national_id')
        role = 'user'
        
        errors = []
        
        if any(u.username == username for u in DB["users"].values()):
            errors.append('اسم المستخدم موجود مسبقاً')
        
        if any(u.email == email for u in DB["users"].values()):
            errors.append('البريد الإلكتروني موجود مسبقاً')
        
        if password != confirm_password:
            errors.append('كلمة المرور غير متطابقة')
        
        if len(password) < 6:
            errors.append('كلمة المرور يجب أن تحتوي على الأقل على 6 أحرف')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            user_id = generate_id('user')
            new_user = User(
                id=user_id,
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                national_id=national_id,
                role=role,
                active=True
            )
            DB["users"][user_id] = new_user
            
            send_notification(
                user_id,
                "مرحباً بك في المنصة",
                f"شكراً لتسجيلك في {DB['settings']['app_name']}! يمكنك الآن إنشاء توكيلاتك الإلكترونية.",
                'success'
            )
            
            flash('تم إنشاء حسابك بنجاح. يمكنك الآن تسجيل الدخول', 'success')
            return redirect(url_for('login'))
    
    register_content = """
    <div class="row justify-content-center">
        <div class="col-md-8 col-lg-6">
            <div class="card shadow border-0 animate__animated animate__fadeIn">
                <div class="card-body p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-user-plus fa-3x gradient-text mb-3"></i>
                        <h2 class="card-title gradient-text">إنشاء حساب جديد</h2>
                        <p class="text-muted">املأ البيانات التالية لإنشاء حسابك</p>
                    </div>
                    <form method="POST">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="first_name" class="form-label fw-bold">الاسم الأول</label>
                                <input type="text" class="form-control" id="first_name" name="first_name" required placeholder="الاسم الأول">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="last_name" class="form-label fw-bold">الاسم الأخير</label>
                                <input type="text" class="form-control" id="last_name" name="last_name" required placeholder="الاسم الأخير">
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="username" class="form-label fw-bold">اسم المستخدم</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-user"></i></span>
                                    <input type="text" class="form-control border-start-0" id="username" name="username" required placeholder="اسم المستخدم">
                                </div>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="email" class="form-label fw-bold">البريد الإلكتروني</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-envelope"></i></span>
                                    <input type="email" class="form-control border-start-0" id="email" name="email" required placeholder="example@email.com">
                                </div>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="password" class="form-label fw-bold">كلمة المرور</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-lock"></i></span>
                                    <input type="password" class="form-control border-start-0" id="password" name="password" required placeholder="كلمة المرور">
                                </div>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="confirm_password" class="form-label fw-bold">تأكيد كلمة المرور</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-lock"></i></span>
                                    <input type="password" class="form-control border-start-0" id="confirm_password" name="confirm_password" required placeholder="تأكيد كلمة المرور">
                                </div>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="phone" class="form-label fw-bold">رقم الهاتف</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-phone"></i></span>
                                    <input type="tel" class="form-control border-start-0" id="phone" name="phone" placeholder="رقم الهاتف">
                                </div>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="national_id" class="form-label fw-bold">رقم الهوية</label>
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0"><i class="fas fa-id-card"></i></span>
                                    <input type="text" class="form-control border-start-0" id="national_id" name="national_id" required placeholder="رقم الهوية">
                                </div>
                            </div>
                        </div>
                        
                        <input type="hidden" name="role" value="user">
                        
                        <div class="alert alert-info border-0">
                            <i class="fas fa-info-circle me-2"></i>
                            يمكنك التسجيل كمستخدم عادي فقط. لحسابات الموثقين يرجى التواصل مع الإدارة.
                        </div>
                        
                        <button type="submit" class="btn btn-primary w-100 py-2 fw-bold">إنشاء حساب</button>
                    </form>
                    <hr class="my-4">
                    <p class="text-center">لديك حساب بالفعل؟ <a href="{{ url_for('login') }}" class="text-decoration-none fw-bold">تسجيل الدخول</a></p>
                </div>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        register_content,
        title="إنشاء حساب - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        now=datetime.utcnow()
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = get_user_stats(current_user.id)
    user_tawkeels = [t for t in DB["tawkeels"].values() if t['user_id'] == current_user.id]
    recent_tawkeels = sorted(user_tawkeels, key=lambda x: x['created_at'], reverse=True)[:5]
    
    unread_notifications = [
        n for n in DB["notifications"].values() 
        if n['user_id'] == current_user.id and not n['is_read']
    ][:5]
    
    dashboard_content = """
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="gradient-text">لوحة التحكم</h2>
            <p class="text-muted">مرحباً {{ current_user.get_full_name() }}, هذه نظرة عامة على حسابك</p>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number">{{ stats.total }}</div>
                    <div class="stat-label text-muted">إجمالي التوكيلات</div>
                    <i class="fas fa-file-contract fa-2x text-primary mt-2 opacity-50"></i>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-warning">{{ stats.pending }}</div>
                    <div class="stat-label text-muted">قيد الانتظار</div>
                    <i class="fas fa-clock fa-2x text-warning mt-2 opacity-50"></i>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-success">{{ stats.approved }}</div>
                    <div class="stat-label text-muted">تم الموافقة</div>
                    <i class="fas fa-check-circle fa-2x text-success mt-2 opacity-50"></i>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-danger">{{ stats.rejected }}</div>
                    <div class="stat-label text-muted">مرفوضة</div>
                    <i class="fas fa-times-circle fa-2x text-danger mt-2 opacity-50"></i>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-lg-8 mb-4">
            <div class="card border-0">
                <div class="card-header bg-transparent border-0 d-flex justify-content-between align-items-center">
                    <h5 class="mb-0 gradient-text">آخر التوكيلات</h5>
                    <a href="{{ url_for('tawkeel_list') }}" class="btn btn-sm btn-primary">عرض الكل</a>
                </div>
                <div class="card-body">
                    {% if recent_tawkeels %}
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>رقم المرجع</th>
                                    <th>نوع التوكيل</th>
                                    <th>الحالة</th>
                                    <th>التاريخ</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for tawkeel in recent_tawkeels %}
                                <tr>
                                    <td class="fw-bold">{{ tawkeel.reference_number }}</td>
                                    <td>{{ templates[tawkeel.template_id].title }}</td>
                                    <td>
                                        {% if tawkeel.status == 'pending' %}
                                        <span class="badge bg-warning">قيد الانتظار</span>
                                        {% elif tawkeel.status == 'approved' %}
                                        <span class="badge bg-success">تم الموافقة</span>
                                        {% elif tawkeel.status == 'rejected' %}
                                        <span class="badge bg-danger">مرفوض</span>
                                        {% elif tawkeel.status == 'expired' %}
                                        <span class="badge bg-secondary">منتهي</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ tawkeel.created_at.strftime('%Y-%m-%d') }}</td>
                                    <td>
                                        <a href="{{ url_for('view_tawkeel', tawkeel_id=tawkeel.id) }}" class="btn btn-sm btn-info">
                                            <i class="fas fa-eye"></i>
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% else %}
                    <div class="text-center py-5">
                        <i class="fas fa-file-contract fa-4x text-muted mb-3 opacity-50"></i>
                        <h4 class="text-muted">لا توجد توكيلات</h4>
                        <p class="text-muted">لم تقم بإنشاء أي توكيلات بعد</p>
                        {% if current_user.role != 'admin' %}
                        <a href="{{ url_for('create_tawkeel') }}" class="btn btn-primary">إنشاء أول توكيل</a>
                        {% endif %}
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="col-lg-4">
            <div class="card mb-4 border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">الإشعارات الحديثة</h5>
                </div>
                <div class="card-body">
                    {% if unread_notifications %}
                    <div class="list-group list-group-flush">
                        {% for notification in unread_notifications %}
                        <a href="{{ notification.link or '#' }}" class="list-group-item list-group-item-action border-0">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">{{ notification.title }}</h6>
                                <small class="text-muted">{{ notification.created_at.strftime('%H:%M') }}</small>
                            </div>
                            <p class="mb-1 text-muted">{{ notification.message }}</p>
                        </a>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div class="text-center py-4">
                        <i class="fas fa-bell-slash fa-2x text-muted mb-2 opacity-50"></i>
                        <p class="text-muted mb-0">لا توجد إشعارات جديدة</p>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="card border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">إجراءات سريعة</h5>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        {% if current_user.role != 'admin' %}
                        <a href="{{ url_for('create_tawkeel') }}" class="btn btn-primary">
                            <i class="fas fa-plus me-2"></i>إنشاء توكيل جديد
                        </a>
                        {% endif %}
                        <a href="{{ url_for('profile') }}" class="btn btn-outline-primary">
                            <i class="fas fa-user me-2"></i>الملف الشخصي
                        </a>
                        <a href="{{ url_for('notifications_page') }}" class="btn btn-outline-secondary">
                            <i class="fas fa-bell me-2"></i>الإشعارات
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        dashboard_content,
        title="لوحة التحكم - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        templates=DB["templates"],
        notifications=DB["notifications"],
        stats=stats,
        recent_tawkeels=recent_tawkeels,
        unread_notifications=unread_notifications,
        now=datetime.utcnow()
    )

@app.route('/tawkeel-list')
@login_required
def tawkeel_list():
    if current_user.role == 'user':
        user_tawkeels = [t for t in DB["tawkeels"].values() if t['user_id'] == current_user.id]
    else: # notary or admin
        user_tawkeels = list(DB["tawkeels"].values())
    
    user_tawkeels = sorted(user_tawkeels, key=lambda x: x['created_at'], reverse=True)

    tawkeel_list_content = """
    <div class="row mb-4">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center">
                <h2 class="gradient-text">قائمة التوكيلات</h2>
                {% if current_user.role != 'admin' %}
                <a href="{{ url_for('create_tawkeel') }}" class="btn btn-primary">
                    <i class="fas fa-plus me-2"></i>إنشاء توكيل جديد
                </a>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="card border-0">
        <div class="card-body">
            {% if user_tawkeels %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>رقم المرجع</th>
                            <th>نوع التوكيل</th>
                            <th>الموكل</th>
                            <th>الوكيل</th>
                            <th>الحالة</th>
                            <th>تاريخ الإنشاء</th>
                            <th>الإجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tawkeel in user_tawkeels %}
                        <tr>
                            <td class="fw-bold">{{ tawkeel.reference_number }}</td>
                            <td>{{ templates[tawkeel.template_id].title }}</td>
                            <td>{{ tawkeel.principal_name }}</td>
                            <td>{{ tawkeel.agent_name }}</td>
                            <td>
                                {% if tawkeel.status == 'pending' %}
                                <span class="badge bg-warning">قيد الانتظار</span>
                                {% elif tawkeel.status == 'approved' %}
                                <span class="badge bg-success">تم الموافقة</span>
                                {% elif tawkeel.status == 'rejected' %}
                                <span class="badge bg-danger">مرفوض</span>
                                {% elif tawkeel.status == 'expired' %}
                                <span class="badge bg-secondary">منتهي</span>
                                {% endif %}
                            </td>
                            <td>{{ tawkeel.created_at.strftime('%Y-%m-%d') }}</td>
                            <td>
                                <a href="{{ url_for('view_tawkeel', tawkeel_id=tawkeel.id) }}" class="btn btn-sm btn-info">
                                    <i class="fas fa-eye"></i>
                                </a>
                                {% if current_user.role in ['notary', 'admin'] and tawkeel.status == 'pending' %}
                                <a href="{{ url_for('approve_tawkeel', tawkeel_id=tawkeel.id) }}" class="btn btn-sm btn-success" onclick="return confirm('هل تريد الموافقة على هذا التوكيل؟')">
                                    <i class="fas fa-check"></i>
                                </a>
                                <a href="{{ url_for('reject_tawkeel', tawkeel_id=tawkeel.id) }}" class="btn btn-sm btn-danger" onclick="return confirm('هل تريد رفض هذا التوكيل؟')">
                                    <i class="fas fa-times"></i>
                                </a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="text-center py-5">
                <i class="fas fa-file-contract fa-4x text-muted mb-3 opacity-50"></i>
                <h4 class="text-muted">لا توجد توكيلات</h4>
                <p class="text-muted">لم يتم إنشاء أي توكيلات بعد</p>
                {% if current_user.role != 'admin' %}
                <a href="{{ url_for('create_tawkeel') }}" class="btn btn-primary">إنشاء أول توكيل</a>
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>
    """
    
    return render_full_template(
        tawkeel_list_content,
        title="قائمة التوكيلات - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        templates=DB["templates"],
        notifications=DB["notifications"],
        user_tawkeels=user_tawkeels,
        now=datetime.utcnow()
    )

@app.route('/create-tawkeel', methods=['GET', 'POST'])
@login_required
def create_tawkeel():
    # *** تعديل: منع الأدمن من إنشاء توكيل ***
    if current_user.role == 'admin':
        flash('لا يمتلك المدير صلاحية إنشاء توكيلات.', 'danger')
        return redirect(url_for('admin_dashboard'))

    template_id = request.args.get('template_id')
    
    if not template_id or template_id not in DB["templates"]:
        selection_content = """
        <div class="row mb-4">
            <div class="col-12">
                <h2 class="gradient-text">اختر نوع التوكيل</h2>
                <p class="text-muted">اختر نوع التوكيل الذي تريد إنشاءه</p>
            </div>
        </div>

        <div class="row">
            {% for template in templates.values() %}
            <div class="col-lg-4 col-md-6 mb-4">
                <div class="card h-100 tawkeel-card border-0">
                    <div class="card-body text-center p-4">
                        <i class="fas {{ template.icon }} feature-icon"></i>
                        <h5 class="card-title fw-bold">{{ template.title }}</h5>
                        <p class="card-text text-muted">{{ template.description }}</p>
                        <a href="{{ url_for('create_tawkeel', template_id=template.id) }}" class="btn btn-primary">إنشاء توكيل</a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        """
        
        return render_full_template(
            selection_content,
            title="اختر نوع التوكيل - " + DB["settings"]["app_name"],
            settings=DB["settings"],
            templates=DB["templates"],
            notifications=DB["notifications"],
            now=datetime.utcnow()
        )
    
    template = DB["templates"][template_id]
    
    if request.method == 'POST':
        # تحويل التواريخ من نص إلى كائنات تاريخ
        effective_date_str = (datetime.now()).strftime('%Y-%m-%d')
        expiration_date_str = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        tawkeel_data = {
            'id': generate_id('tawkeel'),
            'user_id': current_user.id,
            'template_id': template_id,
            'reference_number': generate_reference_number(),
            'principal_name': request.form['principal_name'],
            'principal_national_id': request.form['principal_national_id'],
            'principal_address': request.form.get('principal_address', ''),
            'principal_phone': request.form.get('principal_phone', ''),
            'agent_name': request.form['agent_name'],
            'agent_national_id': request.form['agent_national_id'],
            'agent_address': request.form.get('agent_address', ''),
            'agent_phone': request.form.get('agent_phone', ''),
            'purpose': request.form['purpose'],
            'additional_terms': request.form.get('additional_terms', ''),
            'effective_date': datetime.strptime(effective_date_str, '%Y-%m-%d'),
            'expiration_date': datetime.strptime(expiration_date_str, '%Y-%m-%d'),
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        DB["tawkeels"][tawkeel_data['id']] = tawkeel_data
        
        send_notification(
            current_user.id,
            'تم إنشاء توكيل جديد',
            f'تم إنشاء توكيل جديد برقم مرجعي: {tawkeel_data["reference_number"]}',
            'success',
            url_for('view_tawkeel', tawkeel_id=tawkeel_data['id'])
        )
        
        notaries = [u for u in DB["users"].values() if u.role in ['notary', 'admin']]
        for notary in notaries:
            send_notification(
                notary.id,
                'توكيل جديد يحتاج للمراجعة',
                f'تم إنشاء توكيل جديد برقم {tawkeel_data["reference_number"]} ويحتاج للمراجعة',
                'info',
                url_for('view_tawkeel', tawkeel_id=tawkeel_data['id'])
            )
        
        flash('تم إنشاء التوكيل بنجاح وسيتم مراجعته من قبل الموثق', 'success')
        return redirect(url_for('view_tawkeel', tawkeel_id=tawkeel_data['id']))
    
    create_content = """
    <div class="row justify-content-center">
        <div class="col-lg-10">
            <div class="card shadow border-0">
                <div class="card-header">
                    <h4 class="mb-0 gradient-text">إنشاء توكيل جديد - {{ template.title }}</h4>
                </div>
                <div class="card-body p-4">
                    <form method="POST">
                        <input type="hidden" name="template_id" value="{{ template.id }}">
                        <div class="row">
                            <div class="col-md-6">
                                <h5 class="mb-3 gradient-text">معلومات الموكل (صاحب التوكيل)</h5>
                                <div class="mb-3">
                                    <label for="principal_name" class="form-label fw-bold">اسم الموكل *</label>
                                    <input type="text" class="form-control" id="principal_name" name="principal_name" value="{{ current_user.get_full_name() }}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="principal_national_id" class="form-label fw-bold">رقم هوية الموكل *</label>
                                    <input type="text" class="form-control" id="principal_national_id" name="principal_national_id" value="{{ current_user.national_id }}" required>
                                </div>
                                <div class="mb-3">
                                    <label for="principal_phone" class="form-label fw-bold">رقم هاتف الموكل</label>
                                    <input type="tel" class="form-control" id="principal_phone" name="principal_phone" value="{{ current_user.phone }}">
                                </div>
                                <div class="mb-3">
                                    <label for="principal_address" class="form-label fw-bold">عنوان الموكل</label>
                                    <textarea class="form-control" id="principal_address" name="principal_address" rows="2"></textarea>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <h5 class="mb-3 gradient-text">معلومات الوكيل (المفوض)</h5>
                                <div class="mb-3">
                                    <label for="agent_name" class="form-label fw-bold">اسم الوكيل *</label>
                                    <input type="text" class="form-control" id="agent_name" name="agent_name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="agent_national_id" class="form-label fw-bold">رقم هوية الوكيل *</label>
                                    <input type="text" class="form-control" id="agent_national_id" name="agent_national_id" required>
                                </div>
                                <div class="mb-3">
                                    <label for="agent_phone" class="form-label fw-bold">رقم هاتف الوكيل</label>
                                    <input type="tel" class="form-control" id="agent_phone" name="agent_phone">
                                </div>
                                <div class="mb-3">
                                    <label for="agent_address" class="form-label fw-bold">عنوان الوكيل</label>
                                    <textarea class="form-control" id="agent_address" name="agent_address" rows="2"></textarea>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="mb-3">
                            <label for="purpose" class="form-label fw-bold">الغرض من التوكيل *</label>
                            <textarea class="form-control" id="purpose" name="purpose" rows="6" required>{{ template.template_text }}</textarea>
                            <div class="form-text">يمكنك تعديل النص حسب احتياجك</div>
                        </div>
                        
                        <div class="mb-4">
                            <label for="additional_terms" class="form-label fw-bold">شروط إضافية (اختياري)</label>
                            <textarea class="form-control" id="additional_terms" name="additional_terms" rows="3" placeholder="أي شروط إضافية تريد إضافتها..."></textarea>
                        </div>
                        
                        <div class="alert alert-info border-0">
                            <h6><i class="fas fa-info-circle me-2"></i>معلومات مهمة</h6>
                            <ul class="mb-0">
                                <li>سيتم مراجعة التوكيل من قبل الموثق خلال 24 ساعة.</li>
                                <li>سيتم إشعارك عند الموافقة أو الرفض.</li>
                                <li>التوكيل ساري لمدة سنة واحدة من تاريخ الموافقة.</li>
                            </ul>
                        </div>
                        
                        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                            <a href="{{ url_for('tawkeel_list') }}" class="btn btn-secondary me-md-2">إلغاء</a>
                            <button type="submit" class="btn btn-primary">إرسال للمراجعة</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        create_content,
        title="إنشاء توكيل - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        template=template,
        now=datetime.utcnow()
    )

@app.route('/view-tawkeel/<tawkeel_id>')
@login_required
def view_tawkeel(tawkeel_id):
    if tawkeel_id not in DB["tawkeels"]:
        flash('التوكيل غير موجود', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    tawkeel = DB["tawkeels"][tawkeel_id]
    
    if current_user.role == 'user' and tawkeel['user_id'] != current_user.id:
        flash('ليس لديك صلاحية لعرض هذا التوكيل', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    template = DB["templates"][tawkeel['template_id']]
    
    qr_url = url_for('verify_tawkeel', tawkeel_id=tawkeel_id, _external=True)
    qr_code = generate_qr_code(qr_url)
    
    view_content = f"""
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap">
                <h2 class="gradient-text">تفاصيل التوكيل</h2>
                <div>
                    <a href="{{{{ url_for('tawkeel_list') }}}}" class="btn btn-secondary mb-2"><i class="fas fa-arrow-right me-2"></i>العودة للقائمة</a>
                    {'<a href="' + url_for('download_tawkeel_pdf', tawkeel_id=tawkeel_id) + '" class="btn btn-success mb-2"><i class="fas fa-download me-2"></i>تحميل PDF</a>' if tawkeel['status'] == 'approved' else ''}
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-lg-8">
            <div class="card mb-4 border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">معلومات التوكيل</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <strong>رقم المرجع:</strong> {tawkeel['reference_number']}
                        </div>
                        <div class="col-md-6 mb-3">
                            <strong>نوع التوكيل:</strong> {template['title']}
                        </div>
                        <div class="col-md-6 mb-3">
                            <strong>تاريخ الإنشاء:</strong> {tawkeel['created_at'].strftime('%Y-%m-%d')}
                        </div>
                        <div class="col-md-6 mb-3">
                            <strong>الحالة:</strong>
                            {'<span class="badge bg-warning">قيد الانتظار</span>' if tawkeel['status'] == 'pending' else ''}
                            {'<span class="badge bg-success">تمت الموافقة</span>' if tawkeel['status'] == 'approved' else ''}
                            {'<span class="badge bg-danger">مرفوض</span>' if tawkeel['status'] == 'rejected' else ''}
                            {'<span class="badge bg-secondary">منتهي الصلاحية</span>' if tawkeel['status'] == 'expired' else ''}
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-4 border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">أطراف التوكيل</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6 class="gradient-text">الموكل</h6>
                            <p><strong>الاسم:</strong> {tawkeel['principal_name']}</p>
                            <p><strong>رقم الهوية:</strong> {tawkeel['principal_national_id']}</p>
                            {f'<p><strong>الهاتف:</strong> {tawkeel["principal_phone"]}</p>' if tawkeel['principal_phone'] else ''}
                            {f'<p><strong>العنوان:</strong> {tawkeel["principal_address"]}</p>' if tawkeel['principal_address'] else ''}
                        </div>
                        <div class="col-md-6">
                            <h6 class="gradient-text">الوكيل</h6>
                            <p><strong>الاسم:</strong> {tawkeel['agent_name']}</p>
                            <p><strong>رقم الهوية:</strong> {tawkeel['agent_national_id']}</p>
                            {f'<p><strong>الهاتف:</strong> {tawkeel["agent_phone"]}</p>' if tawkeel['agent_phone'] else ''}
                            {f'<p><strong>العنوان:</strong> {tawkeel["agent_address"]}</p>' if tawkeel['agent_address'] else ''}
                        </div>
                    </div>
                </div>
            </div>

            <div class="card border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">تفاصيل التوكيل</h5>
                </div>
                <div class="card-body">
                    <h6 class="gradient-text">الغرض من التوكيل:</h6>
                    <p class="mb-4" style="white-space: pre-wrap;">{tawkeel['purpose']}</p>
                    
                    {f'<h6 class="gradient-text">شروط إضافية:</h6><p style="white-space: pre-wrap;">{tawkeel["additional_terms"]}</p>' if tawkeel['additional_terms'] else ''}
                </div>
            </div>
        </div>

        <div class="col-lg-4">
            <div class="card mb-4 border-0">
                <div class="card-header bg-transparent border-0">
                    <h5 class="mb-0 gradient-text">رمز التحقق</h5>
                </div>
                <div class="card-body text-center">
                    {'<a href="' + qr_url + '" target="_blank"><img src="data:image/png;base64,' + qr_code + '" alt="QR Code" class="img-fluid mb-3" style="max-width: 200px;"></a><p class="text-muted">امسح الرمز أو اضغط عليه للتحقق من صحة التوكيل</p>' if qr_code else '<p class="text-muted">لا يتوفر رمز تحقق</p>'}
                </div>
            </div>

            {'<div class="card border-0"><div class="card-header bg-transparent border-0"><h5 class="mb-0 gradient-text">إجراءات الموثق</h5></div><div class="card-body"><div class="d-grid gap-2"><a href="' + url_for('approve_tawkeel', tawkeel_id=tawkeel_id) + '" class="btn btn-success" onclick="return confirm(\'هل تريد الموافقة على هذا التوكيل؟\')"><i class="fas fa-check me-2"></i>موافقة</a><a href="' + url_for('reject_tawkeel', tawkeel_id=tawkeel_id) + '" class="btn btn-danger" onclick="return confirm(\'هل تريد رفض هذا التوكيل؟\')"><i class="fas fa-times me-2"></i>رفض</a></div></div></div>' if current_user.role in ['notary', 'admin'] and tawkeel['status'] == 'pending' else ''}
        </div>
    </div>
    """
    
    return render_full_template(
        view_content,
        title="عرض التوكيل - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        tawkeel=tawkeel,
        template=template,
        qr_code=qr_code,
        now=datetime.utcnow()
    )

# =============================================================================
# *** إضافة: مسار التحقق من التوكيل عبر QR Code ***
# =============================================================================
# =============================================================================
# *** إضافة: مسار التحقق من التوكيل عبر QR Code (النسخة المصححة) ***
# =============================================================================
@app.route('/verify-tawkeel/<tawkeel_id>')
def verify_tawkeel(tawkeel_id):
    # التحقق من وجود التوكيل
    if tawkeel_id not in DB["tawkeels"]:
        content = """
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card shadow-lg border-danger">
                    <div class="card-header bg-danger text-white text-center">
                        <i class="fas fa-times-circle fa-3x mb-2"></i>
                        <h2 class="card-title">خطأ في التحقق</h2>
                    </div>
                    <div class="card-body p-4 text-center">
                        <p class="lead">التوكيل الذي تحاول التحقق منه غير موجود.</p>
                        <p class="text-muted">قد يكون رقم التوكيل غير صحيح أو تم حذفه من النظام.</p>
                        <a href="/" class="btn btn-primary mt-3">العودة إلى الصفحة الرئيسية</a>
                    </div>
                </div>
            </div>
        </div>
        """
        # *** التصحيح: تمت إضافة السياق الكامل هنا ***
        return render_full_template(
            content, 
            title="خطأ في التحقق", 
            settings=DB["settings"], 
            notifications={}, 
            now=datetime.utcnow()
        )

    # إذا تم العثور على التوكيل، استمر كالمعتاد
    tawkeel = DB["tawkeels"][tawkeel_id]
    template = DB["templates"][tawkeel['template_id']]
    
    status_map = {
        'approved': ('تمت الموافقة', 'success'),
        'pending': ('قيد الانتظار', 'warning'),
        'rejected': ('مرفوض', 'danger'),
        'expired': ('منتهي الصلاحية', 'secondary')
    }
    status_text, status_color = status_map.get(tawkeel['status'], ('غير معروف', 'dark'))

    verify_content = f"""
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="card shadow-lg">
                <div class="card-header bg-light text-center">
                    <i class="fas fa-check-circle fa-3x text-success mb-2"></i>
                    <h2 class="gradient-text">صفحة التحقق من التوكيل</h2>
                </div>
                <div class="card-body p-4">
                    <div class="alert alert-{status_color} text-center">
                        <h4 class="alert-heading">حالة التوكيل: {status_text}</h4>
                    </div>
                    <h5 class="mt-4">تفاصيل التوكيل الأساسية:</h5>
                    <ul class="list-group list-group-flush">
                        <li class="list-group-item"><strong>رقم المرجع:</strong> {tawkeel['reference_number']}</li>
                        <li class="list-group-item"><strong>نوع التوكيل:</strong> {template['title']}</li>
                        <li class="list-group-item"><strong>اسم الموكل:</strong> {tawkeel['principal_name']}</li>
                        <li class="list-group-item"><strong>اسم الوكيل:</strong> {tawkeel['agent_name']}</li>
                        <li class="list-group-item"><strong>تاريخ الإنشاء:</strong> {tawkeel['created_at'].strftime('%Y-%m-%d')}</li>
                        <li class="list-group-item"><strong>تاريخ الانتهاء:</strong> {tawkeel['expiration_date'].strftime('%Y-%m-%d')}</li>
                    </ul>
                    <div class="text-center mt-4">
                        <p class="text-muted">هذه البيانات تمثل المعلومات الأساسية للتحقق من صحة التوكيل.</p>
                        <a href="{{{{ url_for('index') }}}}" class="btn btn-primary">العودة إلى الصفحة الرئيسية</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_full_template(
        verify_content,
        title="التحقق من التوكيل - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications={},
        now=datetime.utcnow()
    )


@app.route('/download-tawkeel-pdf/<tawkeel_id>')
@login_required
def download_tawkeel_pdf(tawkeel_id):
    if tawkeel_id not in DB["tawkeels"]:
        flash('التوكيل غير موجود', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    tawkeel = DB["tawkeels"][tawkeel_id]
    
    if current_user.role == 'user' and tawkeel['user_id'] != current_user.id:
        flash('ليس لديك صلاحية لتحميل هذا التوكيل', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    if tawkeel['status'] != 'approved':
        flash('يمكن تحميل التوكيلات المعتمدة فقط', 'warning')
        return redirect(url_for('view_tawkeel', tawkeel_id=tawkeel_id))
    
    pdf_buffer = generate_pdf(tawkeel_id)
    if pdf_buffer:
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=tawkeel_{tawkeel["reference_number"]}.pdf'
        return response
    else:
        flash('حدث خطأ أثناء إنشاء ملف PDF. يرجى مراجعة سجلات الخادم.', 'danger')
        return redirect(url_for('view_tawkeel', tawkeel_id=tawkeel_id))

@app.route('/approve-tawkeel/<tawkeel_id>')
@login_required
def approve_tawkeel(tawkeel_id):
    if current_user.role not in ['notary', 'admin']:
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    if tawkeel_id not in DB["tawkeels"]:
        flash('التوكيل غير موجود', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    tawkeel = DB["tawkeels"][tawkeel_id]
    tawkeel['status'] = 'approved'
    tawkeel['approved_at'] = datetime.now()
    tawkeel['approved_by'] = current_user.id
    tawkeel['updated_at'] = datetime.now()
    
    send_notification(
        tawkeel['user_id'],
        'تمت الموافقة على توكيلك',
        f'تمت الموافقة على توكيلك برقم {tawkeel["reference_number"]} من قبل الموثق',
        'success',
        url_for('view_tawkeel', tawkeel_id=tawkeel_id)
    )
    
    flash('تمت الموافقة على التوكيل بنجاح', 'success')
    return redirect(url_for('view_tawkeel', tawkeel_id=tawkeel_id))

@app.route('/reject-tawkeel/<tawkeel_id>')
@login_required
def reject_tawkeel(tawkeel_id):
    if current_user.role not in ['notary', 'admin']:
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    if tawkeel_id not in DB["tawkeels"]:
        flash('التوكيل غير موجود', 'danger')
        return redirect(url_for('tawkeel_list'))
    
    tawkeel = DB["tawkeels"][tawkeel_id]
    tawkeel['status'] = 'rejected'
    tawkeel['rejected_at'] = datetime.now()
    tawkeel['rejected_by'] = current_user.id
    tawkeel['updated_at'] = datetime.now()
    
    send_notification(
        tawkeel['user_id'],
        'تم رفض توكيلك',
        f'تم رفض توكيلك برقم {tawkeel["reference_number"]} من قبل الموثق',
        'danger',
        url_for('view_tawkeel', tawkeel_id=tawkeel_id)
    )
    
    flash('تم رفض التوكيل بنجاح', 'success')
    return redirect(url_for('view_tawkeel', tawkeel_id=tawkeel_id))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        user = DB["users"][current_user.id]
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.phone = request.form.get('phone', user.phone)
        user.national_id = request.form.get('national_id', user.national_id)
        user.updated_at = datetime.now()
        
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                if len(new_password) >= 6:
                    user.password_hash = generate_password_hash(new_password)
                    flash('تم تحديث كلمة المرور بنجاح', 'success')
                else:
                    flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'warning')
            else:
                flash('كلمتا المرور غير متطابقتين', 'danger')

        flash('تم تحديث ملفك الشخصي بنجاح', 'success')
        return redirect(url_for('profile'))

    profile_content = """
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="card shadow border-0">
                <div class="card-header">
                    <h4 class="mb-0 gradient-text">الملف الشخصي</h4>
                </div>
                <div class="card-body p-4">
                    <form method="POST">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="first_name" class="form-label fw-bold">الاسم الأول</label>
                                <input type="text" class="form-control" id="first_name" name="first_name" value="{{ current_user.first_name }}">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="last_name" class="form-label fw-bold">الاسم الأخير</label>
                                <input type="text" class="form-control" id="last_name" name="last_name" value="{{ current_user.last_name }}">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="username" class="form-label fw-bold">اسم المستخدم</label>
                            <input type="text" class="form-control" id="username" value="{{ current_user.username }}" readonly>
                        </div>
                        <div class="mb-3">
                            <label for="email" class="form-label fw-bold">البريد الإلكتروني</label>
                            <input type="email" class="form-control" id="email" value="{{ current_user.email }}" readonly>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="phone" class="form-label fw-bold">رقم الهاتف</label>
                                <input type="tel" class="form-control" id="phone" name="phone" value="{{ current_user.phone or '' }}">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="national_id" class="form-label fw-bold">رقم الهوية</label>
                                <input type="text" class="form-control" id="national_id" name="national_id" value="{{ current_user.national_id or '' }}">
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <h5 class="gradient-text">تغيير كلمة المرور</h5>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="new_password" class="form-label fw-bold">كلمة المرور الجديدة</label>
                                <input type="password" class="form-control" id="new_password" name="new_password" placeholder="اتركها فارغة لعدم التغيير">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="confirm_password" class="form-label fw-bold">تأكيد كلمة المرور</label>
                                <input type="password" class="form-control" id="confirm_password" name="confirm_password">
                            </div>
                        </div>
                        
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">حفظ التغييرات</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        profile_content,
        title="الملف الشخصي - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        now=datetime.utcnow()
    )

@app.route('/notifications')
@login_required
def notifications_page():
    user_notifications = sorted(
        [n for n in DB["notifications"].values() if n['user_id'] == current_user.id],
        key=lambda x: x['created_at'],
        reverse=True
    )
    
    for notification in user_notifications:
        if not notification['is_read']:
            DB['notifications'][notification['id']]['is_read'] = True
        
    notifications_content = """
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="gradient-text">الإشعارات</h2>
        </div>
    </div>
    
    <div class="card border-0">
        <div class="card-body">
            {% if user_notifications %}
            <div class="list-group list-group-flush">
                {% for notification in user_notifications %}
                <a href="{{ notification.link or '#' }}" class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">{{ notification.title }}</h5>
                        <small>{{ notification.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                    </div>
                    <p class="mb-1">{{ notification.message }}</p>
                </a>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-5">
                <i class="fas fa-bell-slash fa-4x text-muted mb-3 opacity-50"></i>
                <h4 class="text-muted">لا توجد إشعارات</h4>
            </div>
            {% endif %}
        </div>
    </div>
    """
    
    return render_full_template(
        notifications_content,
        title="الإشعارات - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        user_notifications=user_notifications,
        now=datetime.utcnow()
    )

@app.route('/notary-dashboard')
@login_required
def notary_dashboard():
    if current_user.role not in ['notary', 'admin']:
        flash('ليس لديك صلاحية الوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))
        
    stats = get_notary_stats()
    pending_tawkeels = sorted(
        [t for t in DB["tawkeels"].values() if t['status'] == 'pending'],
        key=lambda x: x['created_at'],
        reverse=True
    )
    
    notary_dashboard_content = """
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="gradient-text">لوحة تحكم الموثق</h2>
            <p class="text-muted">نظرة عامة على التوكيلات في النظام</p>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number">{{ stats.total }}</div>
                    <div class="stat-label text-muted">إجمالي التوكيلات</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-warning">{{ stats.pending }}</div>
                    <div class="stat-label text-muted">قيد الانتظار</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-success">{{ stats.approved }}</div>
                    <div class="stat-label text-muted">تمت الموافقة</div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-danger">{{ stats.rejected }}</div>
                    <div class="stat-label text-muted">مرفوضة</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card border-0">
        <div class="card-header">
            <h5 class="mb-0 gradient-text">التوكيلات التي تحتاج إلى مراجعة</h5>
        </div>
        <div class="card-body">
            {% if pending_tawkeels %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>رقم المرجع</th>
                            <th>نوع التوكيل</th>
                            <th>الموكل</th>
                            <th>تاريخ الإنشاء</th>
                            <th>الإجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tawkeel in pending_tawkeels %}
                        <tr>
                            <td class="fw-bold">{{ tawkeel.reference_number }}</td>
                            <td>{{ templates[tawkeel.template_id].title }}</td>
                            <td>{{ tawkeel.principal_name }}</td>
                            <td>{{ tawkeel.created_at.strftime('%Y-%m-%d') }}</td>
                            <td>
                                <a href="{{ url_for('view_tawkeel', tawkeel_id=tawkeel.id) }}" class="btn btn-sm btn-info">
                                    <i class="fas fa-eye me-1"></i> عرض ومراجعة
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="text-center py-5">
                <i class="fas fa-check-double fa-4x text-success mb-3 opacity-50"></i>
                <h4 class="text-muted">لا توجد توكيلات قيد الانتظار</h4>
                <p class="text-muted">تمت مراجعة جميع التوكيلات</p>
            </div>
            {% endif %}
        </div>
    </div>
    """
    
    return render_full_template(
        notary_dashboard_content,
        title="لوحة تحكم الموثق - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        templates=DB["templates"],
        notifications=DB["notifications"],
        stats=stats,
        pending_tawkeels=pending_tawkeels,
        now=datetime.utcnow()
    )

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('ليس لديك صلاحية الوصول لهذه الصفحة', 'danger')
        return redirect(url_for('dashboard'))
        
    stats = get_notary_stats()
    all_users = sorted(list(DB["users"].values()), key=lambda u: u.created_at, reverse=True)
    
    admin_dashboard_content = """
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="gradient-text">لوحة تحكم المدير</h2>
            <p class="text-muted">إدارة المستخدمين والنظام</p>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-4 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number">{{ stats.total_users }}</div>
                    <div class="stat-label text-muted">إجمالي المستخدمين</div>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-warning">{{ stats.today_pending }}</div>
                    <div class="stat-label text-muted">توكيلات اليوم (قيد الانتظار)</div>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card stat-card text-center border-0">
                <div class="card-body py-4">
                    <div class="stat-number text-success">{{ stats.today_approved }}</div>
                    <div class="stat-label text-muted">توكيلات اليوم (موافق عليها)</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card border-0">
        <div class="card-header">
            <h5 class="mb-0 gradient-text">إدارة المستخدمين</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>الاسم الكامل</th>
                            <th>اسم المستخدم</th>
                            <th>البريد الإلكتروني</th>
                            <th>الدور</th>
                            <th>الحالة</th>
                            <th>تاريخ التسجيل</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in all_users %}
                        <tr>
                            <td class="fw-bold">{{ user.get_full_name() }}</td>
                            <td>{{ user.username }}</td>
                            <td>{{ user.email }}</td>
                            <td>
                                {% if user.role == 'admin' %}
                                <span class="badge bg-primary">مدير</span>
                                {% elif user.role == 'notary' %}
                                <span class="badge bg-info">موثق</span>
                                {% else %}
                                <span class="badge bg-secondary">مستخدم</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if user.is_active %}
                                <span class="badge bg-success">نشط</span>
                                {% else %}
                                <span class="badge bg-danger">غير نشط</span>
                                {% endif %}
                            </td>
                            <td>{{ user.created_at.strftime('%Y-%m-%d') }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    
    return render_full_template(
        admin_dashboard_content,
        title="لوحة تحكم المدير - " + DB["settings"]["app_name"],
        settings=DB["settings"],
        notifications=DB["notifications"],
        stats=stats,
        all_users=all_users,
        now=datetime.utcnow()
    )

# =============================================================================
# تشغيل التطبيق
# =============================================================================

if __name__ == '__main__':
    with app.app_context():
        init_default_data()
    
    print("=" * 60)
    print(f"تشغيل {DB['settings']['app_name']}")
    print("=" * 60)
    print("رابط التطبيق: http://127.0.0.1:5000")
    print("\nالحسابات الافتراضية:")
    print("  - مدير النظام: admin / admin123")
    print("  - موثق: notary1 / notary123") 
    print("  - مستخدم عادي: user / user123")
    print("\nالمميزات المتاحة بعد التعديل:")
    print("  ✅ تصميم احترافي متكامل")
    print("  ✅ (تم الإصلاح) توكيلات PDF باللغة العربية وبتنسيق احترافي")
    print("  ✅ 8 أنواع مختلفة من التوكيلات")
    print("  ✅ نظام موافقة من قبل الموثق")
    print("  ✅ إشعارات تلقائية")
    print("  ✅ (تم التحسين) رموز QR للتحقق عبر رابط مباشر")
    print("  ✅ تحميل التوكيلات بصيغة PDF")
    print("  ✅ لوحة تحكم متكاملة للمستخدم والموثق والمدير")
    print("  ✅ (تم الإصلاح) الأدمن لا يمكنه إنشاء توكيلات")
    print("  ✅ تصميم متجاوب للجوال")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0')
