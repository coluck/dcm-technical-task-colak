from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from rest_framework import status, parsers
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import TestRunRequest, TestFilePath
from api.serializers import (
  TestRunRequestSerializer,
  TestRunRequestItemSerializer,
  TestFilePathCreateSerializer
)
from api.tasks import execute_test_run_request
from api.usecases import get_assets


class TestRunRequestAPIView(ListCreateAPIView):
    serializer_class = TestRunRequestSerializer
    queryset = TestRunRequest.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        instance = serializer.save()
        execute_test_run_request.delay(instance.id)


class TestRunRequestItemAPIView(RetrieveAPIView):
    serializer_class = TestRunRequestItemSerializer
    queryset = TestRunRequest.objects.all()
    lookup_field = 'pk'


class TestFilePathCreateAPIView(CreateAPIView):
    serializer_class = TestFilePathCreateSerializer
    queryset = TestFilePath.objects.all()
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser]
    

    def perform_create(self, serializer):
        upload_dir = serializer.validated_data.pop('upload_dir')
        test_file_object = serializer.validated_data.pop('test_file')
        
        path = f'{upload_dir}/{test_file_object.name}'

        default_storage.save(f'{settings.BASE_DIR}{path}', ContentFile(test_file_object.read()))
        serializer.validated_data['path'] = path
        serializer.save()


class AssetsAPIView(APIView):

    def get(self, request):
        return Response(status=status.HTTP_200_OK, data=get_assets())
