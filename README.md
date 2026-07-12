# Zyraa - Modern Social Media Platform

Zyraa is a premium, feature-rich social media platform built with Django. It offers a clean, modern user experience similar to Instagram, allowing users to share posts (images & videos), follow other users, customize their profiles, post stories with music, interact via comments and likes, and keep up with their activity via a notification system.

---

## 🚀 Features

### 👤 User Profiles & Interaction
- **Authentication**: Secure user registration, login, and logout.
- **Profiles**: Personalized user profiles with avatars, bios, and follower/following counts.
- **Follow System**: Ability to follow and unfollow other users to customize your feed.

### 📸 Content & Feeds
- **Posts**: Share posts containing captions, images, or videos.
- **Reels / Videos**: Dedicated reels page for browsing video content.
- **Stories**: Upload quick stories with images, videos, and music that expire or show in a feed.
- **Likes & Comments**: Interactive comments section and liking functionality on posts.
- **Bookmarks**: Save posts to your personal collection.

### 🔔 Activity & Notifications
- **Notifications**: Instant notifications for likes, comments, and follow events.

---

## 🛠️ Tech Stack

- **Backend**: [Django](https://www.djangoproject.com/) (Python)
- **Database**: SQLite (Local development) / PostgreSQL (Production ready)
- **Cloud Media Storage**: [Cloudinary](https://cloudinary.com/) (Handles media uploads, including videos and music)
- **Static Assets Serving**: [WhiteNoise](http://whitenoise.evans.io/)
- **Production WSGI Server**: [Gunicorn](https://gunicorn.org/)
- **Frontend**: Responsive HTML5 & Custom CSS3

---

## ⚙️ Configuration & Environment Variables

Zyraa relies on the following environment variables. You can set these in your local environment or use a `.env` file:

| Environment Variable | Description | Default / Example |
|----------------------|-------------|-------------------|
| `SECRET_KEY` | Django security secret key | (Auto-fallback in dev) |
| `DEBUG` | Enable/disable Django debug mode | `True` or `False` |
| `DATABASE_URL` | Connection string for database | `sqlite:///db.sqlite3` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Account Cloud Name | *Required for media uploads* |
| `CLOUDINARY_API_KEY` | Cloudinary API Key | *Required for media uploads* |
| `CLOUDINARY_API_SECRET` | Cloudinary API Secret | *Required for media uploads* |

---

## 💻 Local Setup & Installation

Follow these steps to set up and run Zyraa locally on your machine:

### 1. Clone & Navigate
```bash
git clone <repository-url>
cd Zyraa-main
```

### 2. Set Up Virtual Environment
Create and activate a virtual environment to manage dependencies cleanly:
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migrations
Create the database tables and apply default migrations:
```bash
python manage.py migrate
```

### 5. Create a Superuser (Optional)
To access the Django Admin panel at `/admin/`:
```bash
python manage.py createsuperuser
```

### 6. Start the Development Server
```bash
python manage.py runserver
```
Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## 📁 Media Upload Utility

The project contains a helper script `upload_media.py` to scan and upload files from a local `media/` directory directly to your Cloudinary storage space.

To use it:
1. Ensure your Cloudinary environment variables are set.
2. Run the script:
   ```bash
   python upload_media.py
   ```
