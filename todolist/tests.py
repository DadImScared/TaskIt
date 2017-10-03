
import json
from django.core import mail
from django.test.utils import override_settings
from rest_framework.test import APITestCase
from guardian.shortcuts import assign_perm
from .models import User, TaskList, TaskItem
from .tasks import create_random_user_accounts

# Create your tests here.


def make_data(self):
    self.user = User.objects.create_user('tom', email='fake@test.com', password='password')
    self.my_list = TaskList.objects.create(owner=self.user, name="my first playlist")
    self.my_list.save()


class BaseTestCase(APITestCase):
    """Base test case that all tests inherit from"""

    def setUp(self):
        make_data(self)
        self.client.force_authenticate(user=self.user)


class TaskListsViewTest(APITestCase):
    """Tests TaskLists view"""

    def setUp(self):
        make_data(self)
        self.client.force_authenticate(user=self.user)

    def test_created_lists_view(self):
        response = self.client.get('/lists/')
        self.assertTrue(response.data)


class TaskListViewTest(APITestCase):
    """Tests TaskList view"""

    def setUp(self):
        make_data(self)
        self.client.force_authenticate(user=self.user)

    def test_list_view(self):
        response = self.client.get('/lists/1/')
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.data)

    def test_list_view_with_list_items(self):
        """Todo list should include items"""
        TaskItem.objects.create(name="first list item", creator=self.user, task_list=self.my_list)
        for i in range(20):
            TaskItem.objects.create(name="list item {}".format(i), creator=self.user, task_list=self.my_list)
        response = self.client.get('/lists/1/')
        self.assertTrue('/lists/1/items/1/' in response.data['tasks'][0])


class TaskViewTest(APITestCase):
    """Tests Task view"""

    def setUp(self):
        make_data(self)
        self.client.force_authenticate(user=self.user)
        # TaskItem.objects.create(creator=self.user, task_list=self.my_list, name="my list item")

    def test_create_item(self):
        """Tests post request to create item url"""
        response = self.client.post('/lists/1/items/', data={'name': 'my first list item'})
        self.assertEqual(201, response.status_code)
        self.assertTrue(self.my_list.tasks.all())

    # FIX TEST PERMISSIONS NOT ADDED
    def test_create_item_without_permission(self):
        """post request to create-item url should not be added if user does not have permission"""
        user2 = User.objects.create_user('mary', 'fake2@fake.com', 'password')
        self.client.force_authenticate(user=user2)
        response = self.client.post('/lists/1/items/', data={'name': "other user list item"})
        self.assertEqual(403, response.status_code)


class TaskItemViewTest(BaseTestCase):
    """Tests TaskItemView"""

    def setUp(self):
        super().setUp()
        self.item = TaskItem.objects.create(name="first list item", creator=self.user, task_list=self.my_list)
        self.mary = User.objects.create_user("mary", "fake2@fake.com", "password")
        self.pete = User.objects.create_user("pete", "fake3@fake.com", "password")
        self.my_list.members.add(self.mary)

    def test_unauthorized_user_cant_view_task(self):
        """
        Unauthorized access to a task item should return a 403 status code
        """
        self.client.logout()
        self.client.force_authenticate(user=self.pete)
        response = self.client.get('/lists/1/items/1/')
        self.assertEqual(403, response.status_code)

    def test_authorized_user_can_view_task(self):
        """
        Authorized access to a task item should return task data
        """
        response = self.client.get('/lists/1/items/1/')
        self.assertEqual(response.data, {'name': 'first list item', 'done': False, 'creator': 'tom', 'id': 1})

    def test_authorized_user_can_edit_task_done(self):
        """Authorized users sending a patch request should update the item"""
        # confirm task is not done
        self.assertFalse(self.item.done)
        # confirm user can change
        response = self.client.patch('/lists/1/items/1/', data={"done": True})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.data['done'])
        # confirm item changed in database
        self.item.refresh_from_db()
        self.assertTrue(self.item.done)

    def test_authorized_user_can_edit_task_name(self):
        """Authorized users sending a patch request should update the item"""
        old_name = self.item.name
        response = self.client.patch('/lists/1/items/1/', data={"name": "Name here"})
        self.assertEqual(200, response.status_code)
        new_name = response.data['name']
        self.assertNotEqual(old_name, new_name)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, new_name)

    def test_authorized_user_can_delete_task(self):
        """Authorized users sending a delete request should delete the item"""
        response = self.client.delete('/lists/1/items/1/')
        self.assertEqual(204, response.status_code)
        confirm_404 = self.client.get('/lists/1/items/1/')
        self.assertEqual(404, confirm_404.status_code)

    def test_list_member_with_permission_can_delete_task(self):
        """A member of the todo list should be able to delete tasks if they have permission"""
        assign_perm('delete_taskitem', self.mary, self.item)
        self.client.logout()
        self.client.force_authenticate(user=self.mary)
        response = self.client.delete('/lists/1/items/1/')
        self.assertEqual(204, response.status_code)

    def test_list_member_with_permission_can_edit_task(self):
        """A member of the todo list should be able to edit tasks if they have permission"""
        old_name = self.item.name
        assign_perm('change_taskitem', self.mary, self.item)
        self.client.logout()
        self.client.force_authenticate(user=self.mary)
        response = self.client.patch('/lists/1/items/1/', data={"name": "My new Name"})
        self.assertEqual(200, response.status_code)
        new_name = response.data['name']
        self.assertNotEqual(old_name, new_name)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, new_name)


class ListMembersViewTest(APITestCase):
    """Test list-members view"""

    def setUp(self):
        make_data(self)
        self.client.force_authenticate(user=self.user)

    def test_list_members_view(self):
        """/lists/<list_id>/members/ should return a list of members if user has permission"""
        user2 = User.objects.create_user('mary', 'fake2@fake.com', 'password')
        user2.save()
        self.my_list.members.add(user2)
        response = self.client.get('/lists/1/members/')
        self.assertEqual(200, response.status_code)

    def test_list_members_view_post(self):
        """post request to /lists/<list_id>/members/ should add a new user to the list if creator has permission"""
        user2 = User.objects.create_user('mary', 'fake2@fake.com', 'password')
        user2.save()
        response = self.client.post('/lists/1/members/', data={'email': user2.email})
        self.assertEqual(201, response.status_code)


class CreateTaskReminderViewTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.item = TaskItem.objects.create(creator=self.user, name="first list item", task_list=self.my_list)

    @override_settings(
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_ALWAYS_EAGER=True,
        BROKER_BACKEND='memory',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_create_reminder_successful(self):
        """Creating a reminder should return 201 status code and 'Reminder created' message"""
        response = self.client.post(
            '/lists/1/items/{}/reminder/'.format(self.item.id),
            data=json.dumps({"schedule": {"minutes": 1}}),
            content_type='application/json'
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual("Reminder created", response.data['message'])
        self.assertEqual(1, len(mail.outbox))

    def test_create_reminder_with_bad_item_id(self):
        response = self.client.post(
            '/lists/1/items/255555/reminder/',
            data=json.dumps({"schedule": {"minutes": 1}}),
            content_type="application/json"
        )
        self.assertEqual(404, response.status_code)

    def test_create_reminder_with_bad_list_id(self):
        response = self.client.post(
            '/lists/1424234/items/113142/reminder/',
            data=json.dumps({"schedule": {"minutes": 1}}),
            content_type="application/json"
        )
        self.assertEqual(404, response.status_code)


class ItemPermissionViewTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user2 = User.objects.create_user("mary", "m@test.com", "password")
        self.my_list.members.add(self.user2)
        TaskItem.objects.create(name="first list item", creator=self.user, task_list=self.my_list)

    def test_grant_permission_to_user(self):
        response = self.client.post('/lists/1/items/1/permissions/',
                                    data={"permission": "add_reminder", "list_member": self.user2.id})
        self.assertEqual(201, response.status_code)

    def test_grant_permission_to_user_not_in_list_members(self):
        """
        Granting permission to a user not in the todo list should raise an error
        """
        response = self.client.post('/lists/1/items/1/permissions/',
                                    data={"permission": "add_reminder", "list_member": 25})
        self.assertEqual(400, response.status_code)
        self.assertEqual('User not a member of list', response.data['list_member'][0])

    def test_attempt_grant_permission_to_member_without_authorization(self):
        """
        Granting permission to a user while not authorized to gran permission to the specific item should raise an error
        """
        user = User.objects.create_user("pete", "2r@test.com", "password")
        self.client.logout()
        self.client.force_authenticate(user=user)
        response = self.client.post('/lists/1/items/1/permissions/',
                                    data={"permission": "add_reminder", "list_member": self.user2.id})
        self.assertEqual(403, response.status_code)
