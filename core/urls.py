from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('explore/', views.explore_view, name='explore'),
    path('reels/', views.reels_view, name='reels'),
    path('activity/', views.notifications_view, name='notifications'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/like/<int:post_id>/', views.like_post, name='like_post'),
    path('post/comment/<int:post_id>/', views.comment_post, name='comment_post'),
    path('post/bookmark/<int:post_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('story/create/', views.create_story_view, name='create_story'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('user/<str:username>/follow/', views.follow_user, name='follow_user'),
    path('profile/<str:username>/followers/', views.followers_list, name='followers_list'),
    path('profile/<str:username>/following/', views.following_list, name='following_list'),
    path('api/cloudinary-signature/', views.get_cloudinary_signature, name='cloudinary_signature'),
]
