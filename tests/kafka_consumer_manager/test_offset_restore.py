import mock
import pytest
from kafka.client import KafkaClient
from yelp_kafka.monitoring import ConsumerPartitionOffsets

from yelp_kafka_tool.kafka_consumer_manager. \
    commands.offset_restore import OffsetRestore


class TestOffsetRestore(object):

    topics_partitions = {
        "topic1": [0, 1, 2],
        "topic2": [0, 1, 2, 3],
        "topic3": [0, 1],
    }
    consumer_offsets_metadata = {
        'topic1':
        [ConsumerPartitionOffsets(topic='topic1', partition=0, current=33, highmark=655, lowmark=655)]
    }
    parsed_consumer_offsets = {'group1': {'topic1': {'0': 10, '1': 20}}}
    consumer_offsets_invalid_topic = {'group1': {'topic5': {'0': 10, '1': 20}}}
    consumer_offsets_invalid_partition = {'group1': {'topic1': {'0': 10, '3': 20}}}
    new_consumer_offsets = {'topic1': {0: 10, 1: 20}}
    kafka_consumer_offsets = {'topic1': [
        ConsumerPartitionOffsets(topic='topic1', partition=0, current=30, highmark=40, lowmark=10),
        ConsumerPartitionOffsets(topic='topic1', partition=1, current=20, highmark=40, lowmark=10),
    ]}

    def _get_partition_ids_for_topic(self, topic):
        try:
            return self.topics_partitions[topic]
        # Since we patch sys.exit, let's mask this exception since this call
        # is triggered after the call to sys.exit
        except KeyError:
            pass

    @pytest.fixture
    def mock_kafka_client(self):
        mock_kafka_client = mock.MagicMock(
            spec=KafkaClient
        )
        mock_kafka_client.get_partition_ids_for_topic. \
            side_effect = self._get_partition_ids_for_topic
        return mock_kafka_client

    def test_restore_offsets_invalid_partition(self, mock_kafka_client):
        with mock.patch(
            "yelp_kafka_tool.kafka_consumer_manager."
            "commands.offset_restore.set_consumer_offsets",
            return_value=[],
            autospec=True,
        ), mock.patch.object(
            OffsetRestore,
            "fetch_offsets_kafka",
            spec=OffsetRestore.fetch_offsets_kafka,
            return_value=self.kafka_consumer_offsets,
        ), mock.patch.object(
            OffsetRestore,
            "parse_consumer_offsets",
            spec=OffsetRestore.parse_consumer_offsets,
            return_value=self.consumer_offsets_invalid_partition,
        ), mock.patch(
            'yelp_kafka_tool.kafka_consumer_manager.'
            'commands.offset_restore.KafkaClient',
            spec=KafkaClient.get_partition_ids_for_topic,
            side_effect=self._get_partition_ids_for_topic,
        ):
            # Partition 3 not present in kafka topic topic1
            with pytest.raises(SystemExit) as ex:
                OffsetRestore.restore_offsets(
                    mock_kafka_client,
                    self.consumer_offsets_invalid_partition,
                )

                assert ex.value.code == 1

    def test_restore_offsets_invalid_topic(self, mock_kafka_client):
        with mock.patch(
            "yelp_kafka_tool.kafka_consumer_manager."
            "commands.offset_restore.set_consumer_offsets",
            return_value=[],
            autospec=True,
        ), mock.patch.object(
            OffsetRestore,
            "fetch_offsets_kafka",
            spec=OffsetRestore.fetch_offsets_kafka,
            return_value=self.kafka_consumer_offsets,
        ), mock.patch.object(
            OffsetRestore,
            "parse_consumer_offsets",
            spec=OffsetRestore.parse_consumer_offsets,
            return_value=self.consumer_offsets_invalid_topic,
        ), mock.patch(
            'yelp_kafka_tool.kafka_consumer_manager.'
            'commands.offset_restore.KafkaClient',
            spec=KafkaClient.get_partition_ids_for_topic,
            side_effect=self._get_partition_ids_for_topic,
        ):
            # Topic-5 not present in kafka consumer group-1
            with pytest.raises(SystemExit) as ex:
                OffsetRestore.restore_offsets(
                    mock_kafka_client,
                    self.consumer_offsets_invalid_topic,
                )

                assert ex.value.code == 1

    def test_restore_offsets(self, mock_kafka_client):
        with mock.patch(
            "yelp_kafka_tool.kafka_consumer_manager."
            "commands.offset_restore.set_consumer_offsets",
            return_value=[],
            autospec=True,
        ) as mock_set_offsets, mock.patch.object(
            OffsetRestore,
            "fetch_offsets_kafka",
            spec=OffsetRestore.fetch_offsets_kafka,
            return_value=self.kafka_consumer_offsets,
        ), mock.patch.object(
            OffsetRestore,
            "parse_consumer_offsets",
            spec=OffsetRestore.parse_consumer_offsets,
            return_value=self.parsed_consumer_offsets,
        ), mock.patch(
            'yelp_kafka_tool.kafka_consumer_manager.'
            'commands.offset_restore.KafkaClient',
            spec=KafkaClient.get_partition_ids_for_topic,
            side_effect=self._get_partition_ids_for_topic,
        ):
            OffsetRestore.restore_offsets(mock_kafka_client, self.parsed_consumer_offsets)

            OffsetRestore.fetch_offsets_kafka.assert_called_once_with(
                mock_kafka_client,
                self.parsed_consumer_offsets,
            )

            ordered_args, _ = mock_set_offsets.call_args
            assert ordered_args[1] == 'group1'
            assert ordered_args[2] == self.new_consumer_offsets

    def test_validate_topic_partitions(self, mock_kafka_client):
        topic = "topic1"
        partitions = [0]

        assert OffsetRestore.validate_topic_partitions(
            mock_kafka_client,
            topic,
            partitions,
            self.consumer_offsets_metadata,
        ) is True

    def test_validate_topic_partitions_invalid_topic(self, mock_kafka_client):
        topic = "topic3"
        partitions = [0]

        assert OffsetRestore.validate_topic_partitions(
            mock_kafka_client,
            topic,
            partitions,
            self.consumer_offsets_metadata,
        ) is False

    def test_validate_topic_partitions_invalid_partition(self, mock_kafka_client):
        topic = "topic1"
        partitions = [5]

        assert OffsetRestore.validate_topic_partitions(
            mock_kafka_client,
            topic,
            partitions,
            self.consumer_offsets_metadata,
        ) is False

    def test_build_new_offsets(self, mock_kafka_client):
        new_offsets = OffsetRestore.build_new_offsets(
            mock_kafka_client,
            self.parsed_consumer_offsets,
            self.kafka_consumer_offsets,
        )

        assert new_offsets == self.new_consumer_offsets
