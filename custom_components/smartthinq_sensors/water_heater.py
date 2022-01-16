# REQUIREMENTS = ['wideq']
# DEPENDENCIES = ['smartthinq']

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Tuple

from .wideq.ac import AWHPHotWater

from .wideq.device import WM_DEVICE_TYPES, DeviceType
from .wideq import (
    FEAT_HOT_WATER,
)

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityEntityDescription,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_OPERATION_MODE
)

from homeassistant.const import (
    PRECISION_HALVES,
    STATE_OFF,
    STATE_ON,
    TEMP_CELSIUS,
    PRECISION_WHOLE,
    ATTR_TEMPERATURE
)

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LGEDevice
from .const import DOMAIN, LGE_DEVICES
from .device_helpers import STATE_LOOKUP, LGEBaseDevice, LGEACDevice, get_entity_name

SCAN_INTERVAL = timedelta(seconds=120)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ThinQWaterHeaterEntityDescription(WaterHeaterEntityEntityDescription):
    """A class that describes ThinQ water heater entities."""

AWHP_WATER_HEATER: Tuple[ThinQWaterHeaterEntityDescription, ...] = (
    ThinQWaterHeaterEntityDescription(
        key=FEAT_HOT_WATER,
        name="Water heater",
        icon="mdi:water-boiler",
    ),
)


SUPPORT_FLAGS_HEATER = (
    SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the LGE water heater."""
    _LOGGER.info("Starting LGE ThinQ water heater...")

    lge_water_heater = []
    entry_config = hass.data[DOMAIN]
    lge_devices = entry_config.get(LGE_DEVICES)
    if not lge_devices:
        return

    lge_water_heater.extend(
        [
            LGEWaterHeater(lge_device, water_heater_desc)
            for water_heater_desc in AWHP_WATER_HEATER
            for lge_device in lge_devices.get(DeviceType.AC, [])
            if lge_device.available_features.get(FEAT_HOT_WATER) is not None
        ]
    )

    async_add_entities(lge_water_heater)


class LGEWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Class to control switches for LGE device"""

    entity_description = ThinQWaterHeaterEntityDescription
    _attr_supported_features = SUPPORT_FLAGS_HEATER
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = PRECISION_WHOLE

    def __init__(
            self,
            api: LGEDevice,
            description: ThinQWaterHeaterEntityDescription,

    ):

        """Initialize the water_heater device."""
        super().__init__(api.coordinator)
        self._api = api
        self._wrap_device = LGEACDevice(api)
        self.entity_description = description
        self._attr_name = get_entity_name(api, description.key, description.name)
        self._attr_unique_id = f"{api.unique_id}-{description.key}-water-heater"
        self._attr_device_info = api.device_info

        # TODO: get it from device settings
        self._attr_min_temp = 40
        self._attr_max_temp = 55

        mode_list = [e.value for e in AWHPHotWater]
        self._attr_operation_list = [AWHPHotWater(o).name for o in mode_list]

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        We overwrite coordinator property default setting because we need
        to poll to avoid the effect that after changing switch state
        it is immediately set to prev state. The async_update method here
        do nothing because the real update is performed by coordinator.
        """
        return True

    async def async_update(self) -> None:
        """Update the entity.

        This is a fake update, real update is done by coordinator.
        """
        return

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._api.available

    @property
    def precision(self) -> float:
        """Return the precision of the system."""
        return PRECISION_WHOLE

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._api.state.hot_water_current_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._api.state.hot_water_target_temp

    @property
    def current_operation(self) -> str | None:
        """Return current operation ie. on or off."""
        return self._api.state.hot_water.name

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        temp = round(temp)
        return self._wrap_device.device.set_hot_water_target_temp(temp)

    def set_operation_mode(self, operation_mode):
        return self._wrap_device.device.set_hot_water(operation_mode)
