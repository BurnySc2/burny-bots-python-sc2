"""
Bot made by Burny
Bot version: 0.1
Date of Upload: 2018-06-22

Started working on this bot desgin on 2018-06-19
"""

# pylint: disable=E0602,E1102




import random, json, time, math
# import re, os
# download maps from https://github.com/Blizzard/s2client-proto#map-packs

import sc2 # pip install sc2
from sc2.data import race_gas, race_worker, race_townhalls, ActionResult, Attribute, Race
from sc2 import Race, Difficulty
# from sc2.constants import * # for autocomplete
# from sc2.ids.unit_typeid import *
# from sc2.ids.ability_id import *
import sc2.ids.unit_typeid
import sc2.ids.ability_id
import sc2.ids.buff_id
import sc2.ids.upgrade_id
import sc2.ids.effect_id

# AbilityId.ATTACK

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2, Point3

from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer, Human


from examples import burny_basic_ai
from examples.burny_basic_ai import BehaviorManager


class BuildOrderManager(object):
    def __init__(self):

        ################################
        ######### MACRO (BUILDINGS)
        ################################

        self.buildBarracksCondition = lambda other: \
            all([
                other.units.of_type([SUPPLYDEPOT, SUPPLYDEPOTDROP, SUPPLYDEPOTLOWERED]).ready.exists,
                # and other.townhalls.ready.exists,
                other.already_pending(BARRACKS) < 1,
                other.can_afford(BARRACKS),
                other.units(BARRACKS).amount != 1 or other.townhalls.amount != 1, # TODO: do this if you want to fast expand
                other.supply_used < 180
            ]) 

        self.morphOrbitalCondition = lambda other: other.units(BARRACKS).ready.exists and other.units(COMMANDCENTER).ready.idle.exists

        # self.expandCondition => SEE BURNY BASIC AI FOR EXPANDCONDITION

        ################################
        ######### MACRO (UNITS)
        ################################


        # self.makeWorkersCondition => SEE BURNY BASIC AI
        self.trainMarineCondition = lambda other: other.supply_left > 0 and other.units(BARRACKS).ready.idle.exists

        ################################
        ######### MACRO (UPGRADES)
        ################################

    async def doStuff(self, bot):
        pass

    


class DragonBot(burny_basic_ai.BurnyBasicAI):
    def __init__(self):
        super().__init__()
        pass

    async def firstIterationInit(self):
        await super().firstIterationInit()
        self.bom = BuildOrderManager()

        self.unitTagsInBehaviorManager = set()
        self.behaviorManagers = set()

        # TESTING

        # d = await self._client.query_pathing(self.townhalls.random, self.workers.random.position)
        # d = await self._client.query_pathing(self.townhalls.random.position, self.workers.random.position)
        # d = await self._client.query_pathing(self.workers.random, self.workers.random.position)
        d = await self._client.debug_create_unit(MARINE, 1, self.getMapCenter, 1)

        # d = await self._client.debug_create_unit(MARINE, 2, self.getMapCenter, 1)
    
    async def on_step(self, iteration):
        self.microActions = []
        self.macroActions = []
        if iteration == 0:
            # await super().firstIterationInit()
            await self.firstIterationInit()
        await super().on_step(iteration)

        # testing

        # if iteration == 10:
        #     # testing
        #     thLoc = self.townhalls.random.position3d.towards(self.getMapCenter, 3)
        #     await self._client.debug_text(["THIS LOCATION"], [thLoc])
        #     print("unit height", self.townhalls.random.position3d.z)
        #     print("terrain", self.getTerrainHeight(thLoc))
        #     print("placement", self.inPlacementGrid(thLoc))
        #     print("pathing", self.inPathingGrid(thLoc))
        #     print("visible", self.isVisible(thLoc))
        #     print("hasCreep", self.hasCreep(thLoc))

        #     print()
            
        #     # thLoc = self.townhalls.random.position3d.towards(self.getMapCenter, 13)
        #     thLoc = self.townhalls.random.position3d
        #     await self._client.debug_text(["THIS LOCATION"], [thLoc])
        #     print("unit height", self.townhalls.random.position3d.z)
        #     print("terrain", self.getTerrainHeight(thLoc))
        #     print("placement", self.inPlacementGrid(thLoc))
        #     print("pathing", self.inPathingGrid(thLoc))
        #     print("visible", self.isVisible(thLoc))
        #     print("hasCreep", self.hasCreep(thLoc))

        #     self._game_info.terrain_height.save_image("terrain_height.png")
        #     self._game_info.placement_grid.save_image("placement_grid.png")
        #     self._game_info.pathing_grid.save_image("pathing_grid.png")
        #     self.state.visibility.save_image("visibility.png")
        #     self.state.creep.save_image("creep.png")


        # add new units and set their behavior
        for u in self.units:
            if u.tag not in self.unitTagsInBehaviorManager:
                self.unitTagsInBehaviorManager.add(u.tag)
                manager = BehaviorManager(u.tag)

                if u.type_id == MARINE:
                    manager.attackRange = 5
                    manager.kitingRange = 4.8
                    manager.priorityTypes = [BANELINGCOCOON, BANELING, RAVAGER]
                    manager.ignoreTypes = [OVERLORD, LARVA, EGG]
                    manager.attackRandomLocations = lambda other: set(other.enemy_start_locations) | {x for x in other.known_enemy_structures}
                    manager.attackRandomCondition = lambda other: other.supply_used > 160

                self.behaviorManagers.add(manager)

        # update managers and remove if unit is dead
        deadManagers = []
        microActions = []
        for manager in self.behaviorManagers:
            if manager.removeCondition(self):
                deadManagers.append(manager)
            else:
                await manager.update(self)
                if manager.actionsThisIteration:
                    microActions.extend(manager.actionsThisIteration)
        # print(microActions)
        await self.do_actions(microActions)

        for deadManager in deadManagers:
            self.behaviorManagers.remove(deadManager)

        # testing
        # for u in self.known_enemy_units:
        #     print("enemy unit:", vars(u))



        ################################
        ######### MACRO - in order of priority
        ################################

        # print([
        #         self.units.of_type([SUPPLYDEPOT, SUPPLYDEPOTDROP, SUPPLYDEPOTLOWERED]).ready.exists,
        #         # and self.townhalls.ready.exists,
        #         self.already_pending(BARRACKS) < 1,
        #         bool(self.can_afford(BARRACKS)),
        #         self.units(BARRACKS).amount != 1 or self.townhalls.amount != 1 # TODO: do this if you want to fast expand
        #     ])

        
        # buildings_in_construction = self.units(SUPPLYDEPOT).not_ready
        # if buildings_in_construction.amount > 0:
        #     print(self.already_pending(SUPPLYDEPOT))
        #     ability = self._game_data.units[SUPPLYDEPOT.value].creation_ability
        #     a = sum([o.ability == ability for w in self.workers for o in w.orders]), \
        #     sum([o.ability == ability and Point2((o.target.x, o.target.y)).rounded == s.position.rounded for w in self.workers for o in w.orders for s in buildings_in_construction]), \
        #     buildings_in_construction.amount # might have to end .rounded to points
        #     print(a)

        if self.bom.morphOrbitalCondition(self):
            print("ORBITAL")
            # skip self afford because of orbital "bug"
            # if self.can_afford(ORBITALCOMMAND):
            # if self.can_afford(UPGRADETOORBITAL_ORBITALCOMMAND):
            cc = self.units(COMMANDCENTER).ready.idle.random
            self.macroActions.append(cc(UPGRADETOORBITAL_ORBITALCOMMAND))

        elif self.lowSupplyLeftCondition(self):
            print("DEPOT")
            if self.can_afford(SUPPLYDEPOT):
                ws = self.workers.gathering  
                if ws:
                    w = ws.furthest_to(ws.center)
                    loc = await self.find_placement(SUPPLYDEPOT, w, minDistanceToResources=0, placement_step=1)
                    if loc:
                        self.macroActions.append(w.build(SUPPLYDEPOT, loc))

        elif self.makeWorkersCondition(self):
            print("SCV")
            if self.can_afford(SCV):
                cc = self.townhalls.ready.filter(lambda x: x.is_idle or len(x.orders) == 1 and x.orders[0].progress > 0.6).random
                # cc = self.townhalls.ready.idle.random
                self.macroActions.append(cc.train(SCV))

        elif self.expandCondition(self):
            print("EXPAND")
            # if self.can_afford(COMMANDCENTER):
            await self.basicBuild(COMMANDCENTER)

        # elif self.takeGasCondition(self):
        #     print("GAS")
        #     if self.can_afford(race_gas[self.race]):
        #         vgs = None
        #         for i in range(10):
        #             vgs = self.state.vespene_geyser.closer_than(10, self.townhalls.filter(lambda x: x.build_progress > 0.6).random)
        #             if vgs:
        #                 break
        #         for vg in vgs:
        #             w = self.selectWorker(vg)
        #             if w:
        #                 self.macroActions.append(w.build(race_gas[self.race], vg))

        elif self.bom.trainMarineCondition(self):
            print("MARINE")
            if self.can_afford(MARINE):
                rax = self.units(BARRACKS).ready.idle.random
                self.macroActions.append(rax.train(MARINE))

        elif self.bom.buildBarracksCondition(self):
            print("BARRACKS")
            if self.can_afford(BARRACKS):
                loc = await self.find_placement(BARRACKS, self.townhalls.ready.random, min_distance=5, minDistanceToResources=5, placement_step=4)
                ws = self.workers.gathering
                if loc and ws.exists:
                    w = ws.closest_to(loc)
                    if w:
                        self.macroActions.append(w.build(BARRACKS, loc))




        await self.step_end(iteration)

    async def step_end(self, iteration):
        await super().step_end(iteration)


def main():
    # sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
    #     Bot(Race.Terran, DragonBot()),
    #     Computer(Race.Zerg, Difficulty.VeryHard
    #     )
    # ], realtime=False)

    sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
        Bot(Race.Terran, DragonBot()),
        Computer(Race.Zerg, Difficulty.CheatInsane
        )
    ], realtime=True)

    # sc2.run_game(sc2.maps.get("(2)CatalystLE"), [
    #     Bot(Race.Zerg, DragonBot()),
    #     Computer(Race.Zerg, Difficulty.Medium)
    # ], realtime=False)

if __name__ == '__main__':
    main()