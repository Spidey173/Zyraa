import os
import sys
from pathlib import Path

# Ensure dependencies are installed
try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    print("Cloudinary SDK is not installed. Please run: pip install cloudinary")
    sys.exit(1)

# Retrieve credentials
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET', 'JgyFPK4aQ7qkNNWWqA6Dqmitx3M')

if not cloud_name or not api_key:
    print("Cloudinary credentials not found in environment.")
    cloud_name = input("Enter your Cloudinary Cloud Name: ").strip()
    api_key = input("Enter your Cloudinary API Key: ").strip()

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True
)

media_dir = Path(__file__).resolve().parent / 'media'
if not media_dir.exists():
    print(f"Media directory not found at {media_dir}")
    sys.exit(1)

print(f"Scanning media directory: {media_dir}")
allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.avi', '.mp3', '.wav')

for path in media_dir.rglob('*'):
    if path.is_file() and path.suffix.lower() in allowed_extensions:
        rel_path = path.relative_to(media_dir)
        # Strip the file extension from the public_id as Cloudinary expects public IDs without extensions
        public_id = 'media/' + str(rel_path.with_suffix(''))
        
        print(f"Uploading {rel_path} to Cloudinary...")
        
        # Determine resource type
        ext = path.suffix.lower()
        if ext in ('.mp4', '.mov', '.avi'):
            resource_type = 'video'
        elif ext in ('.mp3', '.wav'):
            resource_type = 'raw'
        else:
            resource_type = 'image'
            
        try:
            cloudinary.uploader.upload(
                str(path),
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
                invalidate=True
            )
            print("  -> Success!")
        except Exception as e:
            print(f"  -> Failed: {e}")

print("\nAll media files uploaded to Cloudinary successfully!")
