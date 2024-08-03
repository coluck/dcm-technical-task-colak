from django.conf import settings

from api.models import TestFilePath, TestEnvironment
from api.serializers import TestFilePathSerializer, TestEnvironmentSerializer


def get_assets():
    return {
        'available_paths': TestFilePathSerializer(TestFilePath.objects.all().order_by('path'), many=True).data,
        'test_envs': TestEnvironmentSerializer(TestEnvironment.objects.all().order_by('name'), many=True).data,
        'upload_dirs': settings.TEST_DIRS_WITHOUT_BASE_DIR,
        # or it can be done like this if the source of truth is the database, but it's not the case here
        # 'upload_dirs': {path.split('/')[0] for path in TestFilePath.objects.values_list('path', flat=True)},
    }
