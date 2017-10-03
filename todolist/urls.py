from django.conf.urls import url

from .views import (TaskListsView,
                    TaskListView, CreateListItem,
                    ListMembersView, TaskItemView,
                    CreateReminderView, ItemPermissionsView)


urlpatterns = [
    url(r'^lists/$', TaskListsView.as_view(), name='user_lists'),
    url(r'^lists/(?P<pk>[0-9]+)/$', TaskListView.as_view(), name='tasklist-detail'),
    url(r'^lists/(?P<list_pk>[0-9]+)/items/$', CreateListItem.as_view(), name='create-item'),
    url(r'^lists/(?P<list_pk>[0-9]+)/items/(?P<pk>[0-9]+)/$', TaskItemView.as_view(), name='taskitem-detail'),
    url(r'^lists/(?P<list_pk>[0-9]+)/items/(?P<pk>[0-9]+)/permissions/$', ItemPermissionsView.as_view(),
        name='item-permissions'),
    url(r'^lists/(?P<list_pk>[0-9]+)/items/(?P<pk>[0-9]+)/reminder/$', CreateReminderView.as_view(),
        name='create-reminder'),
    url(r'^lists/(?P<list_pk>[0-9]+)/members/$', ListMembersView.as_view(), name='list-members')
]
