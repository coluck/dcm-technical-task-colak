from rest_framework import serializers

from api.models import TestRunRequest, TestFilePath, TestEnvironment


class TestRunRequestSerializer(serializers.ModelSerializer):
    env_name = serializers.ReadOnlyField(source='env.name')

    class Meta:
        model = TestRunRequest
        fields = (
            'id',
            'requested_by',
            'env',
            'path',
            'status',
            'created_at',
            'env_name'
        )
        read_only_fields = (
            'id',
            'created_at',
            'status',
            'logs',
            'env_name'
        )


class TestRunRequestItemSerializer(serializers.ModelSerializer):
    env_name = serializers.ReadOnlyField(source='env.name')

    class Meta:
        model = TestRunRequest
        fields = (
            'id',
            'requested_by',
            'env',
            'path',
            'status',
            'created_at',
            'env_name',
            'logs'
        )


class TestFilePathSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestFilePath
        fields = ('id', 'path')



class TestFilePathCreateSerializer(TestFilePathSerializer):
    """ Extended TestFilePathSerializer for creating a new TestFilePath instance """
    upload_dir = serializers.CharField(write_only=True, required=True)
    test_file = serializers.FileField(write_only=True, required=True)

    def validate(self, data):
        test_file = data.get('test_file')

        if not test_file.name.endswith('.py'):
            raise serializers.ValidationError('test_file must be a python file!')

        return data
    
    class Meta(TestFilePathSerializer.Meta):
        fields = TestFilePathSerializer.Meta.fields + ('upload_dir', 'test_file')
        read_only_fields = (
            'id',
            'path'
        )

class TestEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestEnvironment
        fields = ('id', 'name')
