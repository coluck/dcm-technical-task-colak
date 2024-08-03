from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from api.models import TestRunRequest, TestEnvironment, TestFilePath


class TestTestRunRequestAPIView(TestCase):

    def setUp(self) -> None:
        self.env = TestEnvironment.objects.create(name='my_env')
        self.path1 = TestFilePath.objects.create(path='path1')
        self.path2 = TestFilePath.objects.create(path='path2')
        self.url = reverse('test_run_req')

    def test_get_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()
        self.assertEqual([], response_data)

    def test_get_with_data(self):
        for _ in range(10):
            TestRunRequest.objects.create(requested_by='Ramadan', env=self.env)
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()
        self.assertEqual(10, len(response_data))

    def test_post_no_data(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertEqual(
            {
                'env': ['This field is required.'],
                'path': ['This list may not be empty.'],
                'requested_by': ['This field is required.']
            },
            response_data
        )

    def test_post_invalid_path_and_env_id(self):
        response = self.client.post(self.url, data={'env': 'rambo', 'path': "waw", 'requested_by': 'iron man'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertEqual({
            'env': ['Incorrect type. Expected pk value, received str.'],
            'path': ['Incorrect type. Expected pk value, received str.']
        }, response_data)

    def test_post_wrong_path_and_env_id(self):
        response = self.client.post(self.url, data={'env': 500, 'path': 500, 'requested_by': 'iron man'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertEqual({
            'env': ['Invalid pk "500" - object does not exist.'],
            'path': ['Invalid pk "500" - object does not exist.']
        }, response_data)

    @patch('api.views.execute_test_run_request.delay')
    def test_post_valid_multiple_paths(self, task):
        response = self.client.post(
            self.url,
            data={'env': self.env.id, 'path': [self.path1.id, self.path2.id], 'requested_by': 'iron man'}
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        response_data = response.json()
        self.__assert_valid_response(response_data, [self.path1.id, self.path2.id])
        self.assertTrue(task.called)
        task.assert_called_with(response_data['id'])

    @patch('api.views.execute_test_run_request.delay')
    def test_post_valid_one_path(self, task):
        response = self.client.post(self.url, data={'env': self.env.id, 'path': self.path1.id, 'requested_by': 'iron man'})
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        response_data = response.json()
        self.__assert_valid_response(response_data, [self.path1.id])
        self.assertTrue(task.called)
        task.assert_called_with(response_data['id'])

    def __assert_valid_response(self, response_data, expected_paths):
        self.assertIn('created_at', response_data)
        self.assertIn('env', response_data)
        self.assertIn('env_name', response_data)
        self.assertIn('id', response_data)
        self.assertIn('path', response_data)
        self.assertIn('requested_by', response_data)
        self.assertIn('status', response_data)

        self.assertIsNotNone(response_data['created_at'])
        self.assertEqual(self.env.id, response_data['env'])
        self.assertEqual(self.env.name, response_data['env_name'])
        self.assertEqual(expected_paths, response_data['path'])
        self.assertEqual('iron man', response_data['requested_by'])
        self.assertEqual(TestRunRequest.StatusChoices.CREATED.name, response_data['status'])

        self.assertEqual(1, TestRunRequest.objects.filter(requested_by='iron man', env_id=self.env.id).count())


class TestTestRunRequestItemAPIView(TestCase):

    def setUp(self) -> None:
        self.env = TestEnvironment.objects.create(name='my_env')
        self.test_run_req = TestRunRequest.objects.create(
            requested_by='Ramadan',
            env=self.env
        )
        self.path1 = TestFilePath.objects.create(path='path1')
        self.path2 = TestFilePath.objects.create(path='path2')
        self.test_run_req.path.add(self.path1)
        self.test_run_req.path.add(self.path2)
        self.url = reverse('test_run_req_item', args=(self.test_run_req.id, ))

    def test_get_invalid_pk(self):
        self.url = reverse('test_run_req_item', args=(8897, ))
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_get_valid(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_data = response.json()
        self.assertIn('created_at', response_data)
        self.assertIn('env', response_data)
        self.assertIn('env_name', response_data)
        self.assertIn('id', response_data)
        self.assertIn('logs', response_data)
        self.assertIn('path', response_data)
        self.assertIn('requested_by', response_data)
        self.assertIn('status', response_data)

        self.assertIsNotNone(response_data['created_at'])
        self.assertEqual(self.env.id, response_data['env'])
        self.assertEqual(self.env.name, response_data['env_name'])
        self.assertEqual(self.test_run_req.id, response_data['id'])
        self.assertEqual(self.test_run_req.logs, response_data['logs'])
        self.assertEqual([self.path1.id, self.path2.id], response_data['path'])
        self.assertEqual(self.test_run_req.requested_by, response_data['requested_by'])
        self.assertEqual(self.test_run_req.status, response_data['status'])


class TestAssetsAPIView(TestCase):

    def setUp(self) -> None:
        self.url = reverse('assets')

    @patch('api.views.get_assets', return_value={'k': 'v'})
    def test_get(self, _):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'k': 'v'}, response.json())

class TestTestFilePathCreateAPIView(TestCase):


    def setUp(self):
        self.url = reverse('test_file')
        self.valid_test_file_content = b'''
            from django.test import TestCase
            class TestSuccess(TestCase):
                def test_1(self):
                    pass
        '''

    def test_post_no_data(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertEqual(
            {
                'test_file': ['No file was submitted.'],
                'upload_dir': ['This field is required.'],
            },
            response_data
        )
    
    def test_post_invalid_test_file_and_upload_dir(self):
        response = self.client.post(self.url, data={
            'test_file': 'a string more than a file',
            'upload_dir': 42,
        })
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertEqual({
            'test_file': ['The submitted data was not a file. Check the encoding type on the form.']
        }, response_data)

    def test_post_invalid_upload_dir(self):
        response = self.client.post(self.url, data={
            'test_file': SimpleUploadedFile(
                'test_file.py',
                self.valid_test_file_content,
            ),
            'upload_dir': '/invalid-dir',
        })
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertIn('non_field_errors', response_data)
        self.assertIn(
            'upload_dir should be one of the valid directories: ',
            response_data['non_field_errors'][0]
        )
    
    def test_post_invalid_test_file_extension(self):
        response = self.client.post(self.url, data={
            'test_file': SimpleUploadedFile(
                'my_invalid_extension_uploaded_test.txt',
                self.valid_test_file_content,
            ),
            'upload_dir': '/sample-tests',
        })
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        response_data = response.json()
        self.assertIn('non_field_errors', response_data)
        self.assertIn('test_file must be a python file!', response_data['non_field_errors'][0])



    def test_post_valid_test_file_path(self):
        response = self.client.post(self.url, data={
            'test_file': SimpleUploadedFile(
                'my_uploaded_test.py',
                self.valid_test_file_content
            ),
            'upload_dir': '/sample-tests',
        })
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        response_data = response.json()
        self.assertIn('id', response_data)
        self.assertIn('path', response_data)

        self.assertIn('sample-tests/my_uploaded_test', response_data['path'])
        self.assertTrue(TestFilePath.objects.filter(path__icontains='sample-tests/my_uploaded_test').exists())
        # Todo: delete 'my_uploaded_test.py' after the test run successfully, 