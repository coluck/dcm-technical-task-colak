import logging
import subprocess

from celery import shared_task
from django.db import transaction
from django.conf import settings

from api.models import TestRunRequest, TestEnvironment


logger = logging.getLogger(__name__)
MAX_RETRY = 10


def handle_task_retry(instance: TestRunRequest, retry: int) -> None:
    if retry < MAX_RETRY:
        countdown = 2 ** retry
        logger.warning(f'Test Environment is busy, Retrying in {countdown}')
        instance.save_logs(logs=f"Failed to run tests on env {instance.env.name} retrying in {countdown} seconds.")
        instance.mark_as_retrying()
        execute_test_run_request.s(instance.id, retry + 1).apply_async(countdown=countdown)
    else:
        logger.error(
            f"Failed to run tests(ID:{instance.id}) on env {instance.env.name} after retrying {MAX_RETRY} times."
        )
        instance.save_logs(logs=f"Failed to run tests on env {instance.env.name} after retrying {MAX_RETRY} times.")
        instance.mark_as_failed_to_start()


@shared_task
def execute_test_run_request(instance_id: int, retry: int = 0) -> None:
    instance = TestRunRequest.objects.get(id=instance_id)

    with transaction.atomic():
        # use transaction block to ensure that the env is locked and selected for update to prevent race conditions
        env = TestEnvironment.objects.select_for_update().get(name=instance.env.name)
        if env.is_busy():
            handle_task_retry(instance, retry)
            return 

        env.lock()

    try:
        cmd: list = instance.get_command()
        logger.info(f'Running tests(ID:{instance_id}), CMD({" ".join(cmd)}) on env {instance.env.name}')
        instance.mark_as_running()
        
        run = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return_code = run.wait(timeout=settings.TEST_RUN_REQUEST_TIMEOUT_SECONDS)

        instance.save_logs(logs=run.stdout.read())
        if return_code == 0:
            instance.mark_as_success()
        else:
            instance.mark_as_failed()
        
        logger.info(f'tests(ID:{instance_id}), CMD({" ".join(cmd)}) on env {instance.env.name} Completed successfully.')
    
    except subprocess.TimeoutExpired:
        logger.error(f'Timeout occurred while running tests(ID:{instance_id}) on env {instance.env.name}')
        instance.save_logs(logs=f'Timeout occurred while running tests on env {instance.env.name}')
        instance.mark_as_failed()
    
    except Exception as e:
        logger.error(f'Error occurred while running tests(ID:{instance_id}) on env {instance.env.name}: {e}')
        instance.save_logs(logs=f'Error occurred while running tests on env {instance.env.name}: {e}')
        instance.mark_as_failed()
    
    finally:
        env.unlock()

