"""
Basic bot layer made by Burny
Bot layer version: 0.1
Date of Upload: 2018-06-22

Started working on this basic desgin on 2018-06-18
"""

# pylint: disable=E0602,E1102




import random, json, time, math
# import re, os
# download maps from https://github.com/Blizzard/s2client-proto#map-packs

import sc2 # pip install sc2
from sc2.data import race_gas, race_worker, race_townhalls, ActionResult, Attribute, Race
from sc2 import Race, Difficulty
from sc2.constants import * # for autocomplete
# from sc2.ids.unit_typeid import *
# from sc2.ids.ability_id import *
import sc2.ids.unit_typeid
import sc2.ids.ability_id
import sc2.ids.buff_id
import sc2.ids.upgrade_id
import sc2.ids.effect_id

from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2, Point3

from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer, Human

class BehaviorManager(object):
    def __init__(self, unit):
        assert isinstance(unit, (Unit, int))
        if isinstance(unit, Unit):
            self.unitTag = unit.tag
        else:
            self.unitTag = unit
        
        self.removeCondition = lambda other: other.units.find_by_tag(self.unitTag) is None

        self.priorityTypes = None # units that should be focussed first of all units in attackrange, e.g. [SCV, MULE, DRONE, PROBE]
        self.priorityMode = "lowhp" # "lowhp" = attack units with lowest hp first
        # "closest" = attack units closest to this unit first 
        # probably best to have high fire rate (or no projectile) units attack lowest hp and others attack closest

        self.attackRange = None # distance it will be scanned for enemies to attack # TODO: set this automatically to furthest weapon range, e.g. thor = 10, tempest = 15, marine = 5, zergling = i dont know

        self.ignoreTypes = None # units that should be ignored, e.g. banshee should ignore [ZERGLING, HATCHERY, LARVA, EGG]

        self.avoidTypes = None # units that should be avoided, e.g. banshee should avoid [SPORECRAWLER, PHOTONCANNON, MISSILETURRET]
        self.avoidRange = 9 # e.g. marine should avoid baneling and run away from it first, only then split # TODO: look up max vision range of detectors

        self.kitingRange = None # if any enemy is closer than this range, start moving back

        self.splitAllyTypes = None # list of unit types that should be kept distance to
        self.splitEnemyTypes = None # start splitting when enemy of this type is in range (parameter below) to this unit
        self.splitWhenEnemyInRangeOf = 4 # only start splitting when an enemy unit of splitTypes is in range, e.g. start splitting when a tank is in range 13 of this unit # TODO: always split when this is set to None, use 0 when you dont want splitting
        self.splitDistance = 2 # keep distance to other units from splitTypes TODO: look up splash of tanks, banes

        self.attackLocations = None # go to closest location if is not None
        self.attackCondition = None # only attack when condition is met

        self.attackRandomLocations = None # go to random location to find targets
        self.attackRandomCondition = None # only start going to location when condition is met

        self.scoutLocations = None # start scouting any of these locations when scoutCondition is met
        self.scoutCondition = None

        self.retreatLocations = None # retreats to closest location when retreatCondition is met
        self.retreatCondition = None

        # self.idleCondition = None # when to set status to idle?

        self.status = "idle" # vary between ["idle", "retreating", "priotizing", "attacking", "defending", "kiting", "splitting", "avoiding", "casting", "scouting"]

        self.timeLastKiteSplitAvoidIssued = 0
        self.kiteSplitAvoidInterval = 0.001 # how long the bot waits until it issues a new kite/split/avoid command

        self.timeLastAttackIssued = 0
        self.attackRate = 0.61 # TODO: set this automatically to shooting cooldown
        self.attackDelay = 0.1 # leave it 100 ms time to execute the attack before issueing a new command

        self.timeLastCommandIssued = 0 # set this to in-game time when the last command was issued
        self.issueCommandInterval = 0.1 # how long the bot waits until it issues this unit a new command # TODO: automatically set this to the shooting cooldown

        # TODO: use abilities when conditions are met
        self.abilityCondition1 = None
        self.abilityCondition2 = None
        self.abilityCondition3 = None

        # parameters 
        self.attackRangeFix = 0.25

        # variables managed by class / instance:
        self.currentTarget = None
        self.actionsThisIteration = []

    async def update(self, bot):
        self.actionsThisIteration = []
        gameTime = bot.getTimeInSeconds()
        # if self.timeLastCommandIssued + self.issueCommandInterval > gameTime or self.timeLastAttackIssued + self.attackDelay > gameTime:
        if self.timeLastCommandIssued + self.issueCommandInterval > gameTime:
            return # trying to issue commands too fast
        unit = bot.units.find_by_tag(self.unitTag)
        # if self.removeCondition(bot):
        if not unit:
            print("bot is trying to update a dead unit")
            return # unit is dead
        issuedCommand = False

        """ unit behavior priority
        - set status to idle if idle condition met 
        - (use ability if we have energy and ability off cooldown and ability condition is met)
        - retreat if we are not retreating and condition is met (or only condition is met?)
        - kite if conditions met
        - split if conditions met
        - avoid units in avoidTypes
        - attack priority targets if available
        - attack any other targets in range if not in ignoreTypes
        - move to random target from attackLocations if attackcondition is met, the timeLastIssued will prevent spamming too hard
        - move to random scoutlocation if scout condition is met        
        - else do nothing
        """

    

        if self.status == "movingToTarget":
            if unit.distance_to(self.currentTarget) < 2:
                self.status = "idle"
            elif unit.is_idle:
                self.status = "idle"

        # TODO: ability usage

        if self.status != "retreating" \
            and self.retreatLocations \
            and self.retreatCondition \
            and self.retreatLocations(bot) \
            and self.retreatCondition(bot):

            retreatLocation = random.choice(self.retreatLocations(bot))
            # TODO: change this so it moves away from units that can attack it first, then move to retreat location
            self.status = "retreating"
            self.timeLastCommandIssued = gameTime
            self.actionsThisIteration.append(unit.move(retreatLocation))
            issuedCommand = True
            return
    
        if unit.weapon_cooldown != 0:# and self.timeLastKiteSplitAvoidIssued + self.kiteSplitAvoidInterval < gameTime:
            if self.kitingRange \
                and bot.known_enemy_units.not_structure.closer_than(self.kitingRange, unit).filter(lambda u: not u.is_snapshot).exists:

                self.status = "kiting"
                closeEnemies = bot.known_enemy_units.not_structure.closer_than(self.kitingRange, unit).filter(lambda u: not u.is_snapshot)
                closestEnemy = closeEnemies.closest_to(unit)
                distClosestEnemy = unit.distance_to(closestEnemy)
                distToMaxRange = round(self.attackRange - distClosestEnemy, 3)
                distToMaxRange = max(1, min(distToMaxRange, self.attackRange))
                locations = bot.getPointsAroundUnit(unit, minDistance=distToMaxRange/4, maxDistance=distToMaxRange, stepSize=distToMaxRange/4, pointsPerCircle=32)
                terrainHeightAtUnit = bot.getTerrainHeight(unit.position.to2)                
                locationsFiltered = {p for p in locations if bot.inPathingGrid(p) and (unit.distance_to(p) < 2.5 or abs(bot.getTerrainHeight(p) - terrainHeightAtUnit) < 10)}
                if locationsFiltered:
                    self.timeLastCommandIssued = gameTime
                    self.timeLastKiteSplitAvoidIssued = gameTime
                    kiteLocation = closestEnemy.position.furthest(locationsFiltered)
                    issuedCommand = True                
                    self.actionsThisIteration.append(unit.move(kiteLocation))

            elif self.status != "splitting" \
                and (self.splitWhenEnemyInRangeOf is None \
                or self.splitWhenEnemyInRangeOf > 0 \
                and self.splitEnemyTypes \
                and bot.known_enemy_units.of_type(self.splitEnemyTypes).closer_than(self.splitWhenEnemyInRangeOf, unit).exists) \
                and self.splitAllyTypes \
                and bot.units.tags_not_in([unitTag]).of_type(self.splitAllyTypes).closer_than(self.splitDistance, unit):

                self.status = "splitting"
                self.timeLastCommandIssued = gameTime
                self.timeLastKiteSplitAvoidIssued = gameTime
                locations = bot.getPointsAroundUnit(unit, minDistance=0.5, maxDistance=1, stepSize=0.5, pointsPerCircle=16)
                locationsFiltered = {p for p in locations if bot.inPathingGrid(p)}
                if locationsFiltered:
                    closeAllies = bot.units.tags_not_in([unitTag]).of_type(self.splitAllyTypes).closer_than(self.splitDistance, unit)
                    closestAlliedUnit = closeAllies.closest_to(unit)
                    splitLocation = closestAlliedUnit.position.furthest(locationsFiltered)
                    issuedCommand = True
                    self.actionsThisIteration.append(unit.move(splitLocation))
        
            elif self.status != "avoiding" \
                and self.avoidTypes \
                and self.avoidRange \
                and bot.known_enemy_units.of_type(self.avoidTypes).closer_than(self.avoidRange, unit).exists:

                self.status = "avoiding"
                self.timeLastCommandIssued = gameTime
                self.timeLastKiteSplitAvoidIssued = gameTime
                locations = bot.getPointsAroundUnit(unit, minDistance=3, maxDistance=5, stepSize=1, pointsPerCircle=8)
                locationsFiltered = {p for p in locations if bot.inPathingGrid(p)}
                if locationsFiltered:
                    closeEnemies = bot.known_enemy_units.of_type(self.avoidTypes).closer_than(self.avoidRange, unit)
                    enemiesCenter = closeEnemies.center
                    avoidLocation = enemiesCenter.furthest(locationsFiltered)
                    issuedCommand = True
                    self.actionsThisIteration.append(unit.move(avoidLocation))

        if unit.weapon_cooldown == 0: 
            # priority attacks
            if self.priorityTypes \
                and self.attackRange \
                and bot.known_enemy_units.of_type(self.priorityTypes).closer_than(self.attackRange + self.attackRangeFix, unit).exists:

                priotizeUnits = bot.known_enemy_units.of_type(self.priorityTypes).closer_than(self.attackRange + self.attackRangeFix, unit)
                if self.priorityMode == "lowhp":
                    priotizeUnits = priotizeUnits.sorted(lambda u: u.health_percentage, reverse=True)
                elif self.priorityMode == "closest":
                    priotizeUnits = priotizeUnits.sorted(lambda u: u.distance_to(unit), reverse=True)

                if not issuedCommand:# and self.timeLastAttackIssued + self.attackRate < gameTime:
                    self.status = "priotizing"
                    self.timeLastCommandIssued = gameTime
                    self.timeLastAttackIssued = gameTime
                    issuedCommand = True
                    target = priotizeUnits.pop() # it will use the last target in list, thats why i used reverse=True
                    self.actionsThisIteration.append(unit.attack(target))

                for i in range(priotizeUnits.amount):
                    if i > 3 or i+1 == priotizeUnits.amount:
                        self.actionsThisIteration.append(unit.attack(priotizeUnits[-(i+1)].position, queue=True))
                        break
                    self.actionsThisIteration.append(unit.attack(priotizeUnits[-(i+1)], queue=True))
                return

            # attack units in range
            if self.attackRange \
                and (self.ignoreTypes
                and bot.known_enemy_units.exclude_type(self.ignoreTypes).closer_than(self.attackRange + self.attackRangeFix, unit).exists
                or bot.known_enemy_units.closer_than(self.attackRange + self.attackRangeFix, unit).exists):
                # or bot.known_enemy_units.closer_than(self.attackRange + self.attackRangeFix, unit).exists):

                if self.ignoreTypes:
                    targetUnits = bot.known_enemy_units.exclude_type(self.ignoreTypes).closer_than(self.attackRange + self.attackRangeFix, unit)
                else:
                    targetUnits = bot.known_enemy_units.closer_than(self.attackRange + self.attackRangeFix, unit)

                if self.priorityMode == "lowhp":
                    targetUnits = targetUnits.sorted(lambda u: u.health_percentage, reverse=True)
                elif self.priorityMode == "closest":
                    targetUnits = targetUnits.sorted(lambda u: u.distance_to(unit), reverse=True)

                # targetUnits = targetUnits.sorted(lambda u: u.distance_to(unit), reverse=True) # sort by closest

                if targetUnits: # sometimes it is empty and i dont know why
                    if not issuedCommand:# and self.timeLastAttackIssued + self.attackRate < gameTime:
                        self.status = "attacking"
                        self.timeLastCommandIssued = gameTime
                        self.timeLastAttackIssued = gameTime
                        issuedCommand = True
                        target = targetUnits.pop() # it will use the last target in list, thats why i used reverse=True
                        if target.is_structure:
                            self.actionsThisIteration.append(unit.attack(target.position))
                        else:
                            self.actionsThisIteration.append(unit.attack(target))

                    for i in range(targetUnits.amount):
                        if i > 3 or i+1 == targetUnits.amount:
                            self.actionsThisIteration.append(unit.attack(targetUnits[-(i+1)].position, queue=True))
                            break
                        self.actionsThisIteration.append(unit.attack(targetUnits[-(i+1)], queue=True))
                return

        if unit.weapon_cooldown == 0 and self.status != "movingToTarget":
            if self.attackLocations \
                and self.attackCondition \
                and self.attackLocations(bot) \
                and self.attackCondition(bot):
                
                self.status = "movingToTarget"
                self.timeLastCommandIssued = gameTime
                issuedCommand = True
                self.currentTarget = unit.position.closest(self.attackLocations(bot)).position.to2
                self.actionsThisIteration.append(unit.move(self.currentTarget))
                return

            if self.attackRandomLocations \
                and self.attackRandomCondition \
                and self.attackRandomLocations(bot) \
                and self.attackRandomCondition(bot):
                
                self.status = "movingToTarget"
                self.timeLastCommandIssued = gameTime
                issuedCommand = True
                self.currentTarget = random.choice(list(self.attackRandomLocations(bot))).position.to2
                self.actionsThisIteration.append(unit.move(self.currentTarget))
                return

            if self.scoutLocations \
                and self.scoutCondition \
                and self.scoutLocations(bot) \
                and self.scoutCondition(bot):
                
                self.status = "movingToTarget"
                self.timeLastCommandIssued = gameTime
                issuedCommand = True
                self.currentTarget = random.choice(list(self.scoutLocations(bot))).position.to2
                self.actionsThisIteration.append(unit.move(self.currentTarget))
                return
































class BurnyBasicAI(sc2.BotAI):
    def __init__(self):
        self.allowedHandleIdleWorkers = True
        self.allowedHandleLongDistanceMining = True
        self.allowedBalanceSaturation = True
        self.allowedHandleMules = True
        self.allowedSplitWorkers = True
        self.allowedSetRallyPoints = True
        self.allowedHandleDepots = True
        self.allowedHandleRepairs = True
        self.allowedBuildingCancelMicro = True
        self.allowedFlyingCoommandCenters = True

        self.baseToMineralsCenterDistance = 10 # set this to lower later so we can detect misplaced commandcenters

        self.microActions = []
        self.macroActions = []

        self.expandCondition = lambda other: \
            any([
                # either we are in late game, then count mineral fields near townhalls
                all([
                    other.townhalls,
                    other.getTimeInSeconds() > 10*60,
                    other.state.mineral_field.amount > 0,

                    sum([other.state.mineral_field.closer_than(10, x).amount for x in other.townhalls]) 
                    >= 2 * (other.workers.amount + other.geysers.filter(lambda g: g.has_vespene).amount) 
                    - 3 * other.geysers.filter(lambda g: g.has_vespene).amount,

                    sum(other.already_pending(x) for x in [COMMANDCENTER, NEXUS, HATCHERY]) < 1,
                    other.units.of_type([COMMANDCENTER, NEXUS, HATCHERY]).not_ready.amount < 1,
                ]),                    
                # or early game (count gas too because workers in gas are not part of self.workers)
                all([
                    other.townhalls,
                    other.getTimeInSeconds() <= 10*60,
                    # any([
                    #     hasattr(other, "buildExpansionDict") and not other.buildExpansionDict,
                    #     hasattr(other, "buildExpansionDict") and other.buildExpansionDict and any([other.can_afford(x) for x in race_townhalls[other.race]]),
                    # ]),
                    other.workers.amount + other.already_pending(race_worker[other.race])
                    >= 18 + 1 * int(other.race == Race.Terran) + 2 * int(other.race == Race.Protoss),

                    other.workers.amount + other.geysers.ready.filter(lambda g: g.has_vespene).amount + other.already_pending(race_worker[other.race]) + 8 >= 16 * other.townhalls.amount + 3 * other.geysers.ready.filter(lambda g: g.has_vespene).amount, # the +8 acts as a parameter here, can vary from 0 to +16
                    sum(other.already_pending(x) for x in [COMMANDCENTER, NEXUS, HATCHERY]) < 1,                    
                    # other.units.of_type([COMMANDCENTER, NEXUS, HATCHERY]).not_ready.amount < 1, # TODO: comment out if you only want to expand when not making a main building already
                ])
            ])
        
        self.makeWorkersCondition = lambda other: \
            all([
                other.supply_left > 0,
                other.supply_used < 198,
                any([
                    all([
                        self.getTimeInSeconds() > 25*60,
                        other.workers.amount + other.geysers.ready.filter(lambda g: g.has_vespene).amount + other.already_pending(race_worker[other.race]) < 20 + 14 * int(other.race == Race.Zerg),  # TODO: change back to 66
                    ]),
                    all([
                        self.getTimeInSeconds() > 15*60,
                        other.workers.amount + other.geysers.ready.filter(lambda g: g.has_vespene).amount + other.already_pending(race_worker[other.race]) < 50 + 14 * int(other.race == Race.Zerg),  # TODO: change back to 66
                    ]),
                    all([
                        self.getTimeInSeconds() <= 15*60,
                        other.workers.amount + other.geysers.ready.filter(lambda g: g.has_vespene).amount + other.already_pending(race_worker[other.race]) < 100 + 14 * int(other.race == Race.Zerg),  # TODO: change back to 66
                    ])                    
                ]),                
                any([
                    other.race != Race.Zerg
                    and (other.townhalls.ready.idle.exists or other.townhalls.ready.filter(lambda x: x.is_idle or len(x.orders) == 1 and x.orders[0].progress > 0.75).exists), # the "progress" is a fix so that an scv is always in the queue
                    other.race == Race.Zerg
                    and other.units(LARVA).exists
                ])
            ])

        self.timeLastGasTaken = 0
        self.takeGasCondition = lambda other: \
            all([
                other.supply_used >= 16 + 2 * int(other.race == Race.Protoss) + 4 * int(other.race == Race.Zerg),
                other.timeLastGasTaken > 30 - 20 * int(other.race == Race.Zerg),
                other.already_pending(race_gas[other.race]) < 1,
                other.geysers.filter(lambda g: g.has_vespene).amount <= 6 + 2 * int(other.race != Race.Terran),
                self.state.vespene_geyser.filter(lambda x: x.has_vespene).closer_than(10, self.townhalls.filter(lambda x: x.build_progress > 0.6).random).exists
            ])
        
        productionBuildings = {BARRACKS, GATEWAY, WARPGATE, HATCHERY, LAIR, HIVE} # 1 supply per 18 sec
        productionBuildings2 = {FACTORY, STARPORT, ROBOTICSFACILITY, STARGATE} # 2 supply per 18 sec
        supplyGiving = {SUPPLYDEPOT, SUPPLYDEPOTLOWERED, OVERLORD, PYLON}  # units giving 8 supply, dont add supplyDrop here
        self.lowSupplyLeftCondition = lambda other: \
            all([
                    8 * sum(other.already_pending(x) for x in supplyGiving)
                    + 8 * other.units.of_type(supplyGiving).not_ready.amount
                    + other.supply_cap
                    < 200,
                other.townhalls.exists,
                other.supply_used >= 13 + int(other.race != Race.Zerg),

                    (other.units.of_type(set(race_townhalls[other.race]) | productionBuildings).filter(lambda u: u.build_progress > 0.6).amount 
                    + 2 * other.units.of_type(productionBuildings2).filter(lambda u: u.build_progress > 0.6).amount
                    # - 8 * sum(other.already_pending(x) for x in supplyGiving) 
                    - 8 * other.units.of_type(supplyGiving).not_ready.amount # in construction / overlords training
                    - 15 * other.units.of_type([COMMANDCENTER, NEXUS, HATCHERY]).not_ready.filter(lambda u: u.build_progress > 0.8).amount / (1 + 3 * int(other.race == Race.Zerg)))
                    # - 15 * sum(other.already_pending(x) for x in [COMMANDCENTER, NEXUS, HATCHERY]) / (5 * (1 + 3 * int(other.race == Race.Zerg)))

                    * ((19 + 3 * int(other.race == Race.Terran)) / 18) # ideally should be 21 / 18 for terran because of 18 marine build time and 21 depot build time
                    > other.supply_left, # because terran for some reason has 3 sec longer build time on depots -> build depots earlier by fraction

                sum(other.already_pending(x) for x in supplyGiving) < 1
            ])

    async def firstIterationInit(self):
        self.splitWorkers()
    
    async def on_step(self, iteration):
        if iteration == 0:
            await self.firstIterationInit()
        self.handleIdleWorkers()
        if iteration % 50 == 0: # save performance
            await self.distribute_workers()
        if (iteration + 25) % 50 == 0:
            self.handleLongDistanceMining()
        if iteration % 10 == 0: # save performance
            await self.distribute_workers(onlySaturateGas=True)
        self.handleMules() # terran
        self.setWorkerRallyPoint()
        self.handleDepots() # terran
        self.handleRepair() # terran
        self.handleBuildingCancelMicro()
        # self.handleMisplacedCommandCenter()



        

    async def step_end(self, iteration):
        if self.microActions:
            await self.do_actions(self.microActions)
        if self.macroActions:
            await self.do_actions(self.macroActions)

    def getTerrainHeight(self, pos):
        # returns terrain height at pos, good for walling (at chokes and ramps) and to find out where the main base ends
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self._game_info.terrain_height[(pos)] # returns int

    def inPlacementGrid(self, pos):
        # returns True if it is possible to build a structure at pos
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self._game_info.placement_grid[(pos)] == 0

    def inPathingGrid(self, pos):
        # returns True if it is possible for a ground unit to move to pos
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self._game_info.pathing_grid[(pos)] != 0

    def isVisible(self, pos):
        # returns True if the area at pos is visible
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self.state.visibility[(pos)] #== 0 # TODO: have to talk to dentosal how to fix 1 and 0 values

    def hasCreep(self, pos):
        # returns True if there is creep at position
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self.state.creep[(pos)] #== 1 # TODO: have to talk to dentosal how to fix 1 and 0 values

    def getTimeInSeconds(self):
        # returns real time if game is played on "faster"
        return self.state.game_loop * 0.725 * (1/16)

    def getPointsAroundUnit(self, unit, minDistance=10, maxDistance=10, stepSize=1, pointsPerCircle=8):
        # e.g. locationAmount=4 would only consider 4 points: north, west, east, south
        assert isinstance(unit, (Unit, Point2, Point3))
        loc = unit.position.to2
        # minDistance = max(1, round(minDistance))
        # maxDistance = max(1, minDistance, round(maxDistance))
        stepSize = max(0.001, stepSize)
        pointsPerCircle = max(1, round(pointsPerCircle))
        positions = []
        distance = minDistance
        while distance <= maxDistance:
            positions += [Point2(( \
            loc.x + distance * math.cos(math.pi * 2 * alpha / pointsPerCircle), \
            loc.y + distance * math.sin(math.pi * 2 * alpha / pointsPerCircle))) \
            for alpha in range(pointsPerCircle)]
            distance += stepSize
        # positions = [Point2(( \
        #     loc.x + distance * math.cos(math.pi * 2 * alpha / pointsPerCircle), \
        #     loc.y + distance * math.sin(math.pi * 2 * alpha / pointsPerCircle))) \
        #     for alpha in range(pointsPerCircle) # alpha is the angle
        #     for distance in range(minDistance, maxDistance+1, stepSize)]
        return positions

    @property
    def getMapCenter(self):
        return self._game_info.map_center

    @property
    def getPlayableArea(self):
        return self._game_info.playable_area # returns x0, y0, x1, y1 coordinates of the playable area    

    @property
    def enemyRace(self):
        self.enemy_id = 3 - self.player_id
        return Race(self._game_info.player_races[self.enemy_id])
    
    # async def getEnemyRace(self): # only works in 1 vs 1
    #     players = (await self._client.get_game_info()).players
    #     myPlayerId = next((x.id for x in players if x.race == self.getUnitInfo(self.units.random, "race")), 1)
    #     enemyId = 3 - myPlayerId # id is 1 or 2 for the players, so the sum is 3
    #     enemyRace = players[enemyId - 1].race
    #     # make a dictionary with 
    #     # races = {Race.Terran.Value: "t"} # or "terran" and so forth
    #     # => races[enemyRace] returns string of race then
    #     return enemyRace

    async def getRampPoints(self, returnOneSet=True):
        ramps = (await self._client.get_game_info()).map_ramps # list
        if returnOneSet:
            allRampPoints = set().union(*[ramp._points for ramp in ramps]) # a set of tuples
            return allRampPoints
        else:
            rampsWithPoints = [ramp._points for ramp in ramps] # a list of sets of tuples
            return rampsWithPoints # each list entry is one ramp, each ramp has multiple points as tuples

    # TODO: from the score_pb2.py, get collection rate minerals and vespene and other score data (but the latter is optional)

    ################################
    ######### OVERWRITING DEFAULT FUNCTIONS
    ################################

    async def find_placement(self, building, near, max_distance=20, random_alternative=False, placement_step=3, min_distance=0, minDistanceToResources=3):
        """Finds a placement location for building."""

        assert isinstance(building, (AbilityId, UnitTypeId))
        assert isinstance(near, (Point2, Point3, Unit))
        near = near.position.to2

        if isinstance(building, UnitTypeId):
            building = self._game_data.units[building.value].creation_ability
        else: # AbilityId
            building = self._game_data.abilities[building.value]

        if await self.can_place(building, near):
            return near

        for distance in range(min_distance, max_distance, placement_step):
            possible_positions = [Point2(p).offset(near).to2 for p in (
                [(dx, -distance) for dx in range(-distance, distance+1, placement_step)] +
                [(dx,  distance) for dx in range(-distance, distance+1, placement_step)] +
                [(-distance, dy) for dy in range(-distance, distance+1, placement_step)] +
                [( distance, dy) for dy in range(-distance, distance+1, placement_step)]
            )]
            if (self.townhalls | self.state.mineral_field | self.state.vespene_geyser).exists and minDistanceToResources > 0: 
                possible_positions = [x for x in possible_positions if (self.state.mineral_field | self.state.vespene_geyser).closest_to(x).distance_to(x) >= minDistanceToResources] # filter out results that are too close to resources

            res = await self._client.query_building_placement(building, possible_positions)
            possible = [p for r, p in zip(res, possible_positions) if r == ActionResult.Success]
            if not possible:
                continue

            if random_alternative:
                return random.choice(possible)
            else:
                return min(possible, key=lambda p: p.distance_to(near))
        return None

    async def basicBuild(self, buildingType, location=None, worker=None, buildAsWall=False, expandOnLocation=True):
        if not hasattr(self, "buildExpansionDict"):
            self.buildExpansionDict = {}
        if self.buildExpansionDict:
            wTag = list(self.buildExpansionDict.keys())[0]
            if self.buildExpansionDict[wTag]["expireTime"] < self.getTimeInSeconds():
                self.buildExpansionDict.pop(wTag)

        townhallTypes = [NEXUS, HATCHERY, COMMANDCENTER]

        if buildAsWall:
            pass
        elif buildingType in townhallTypes:
            # is townhall, build it on expansion
            if not self.buildExpansionDict: # if dict empty
                if not expandOnLocation and not self.can_afford(buildingType):
                    return

                if expandOnLocation:
                    if not location:
                        location = await self.get_next_expansion()
                    if location:
                        
                        loc = await self.find_placement(buildingType, near=location, random_alternative=False, minDistanceToResources=5, placement_step=1)
                        w = worker or self.selectWorker(loc)
                        if w:
                            # print("adding worker to dict", w.tag, loc, buildingType)
                            self.buildExpansionDict[w.tag] = {
                                "location": loc,
                                "buildingType": buildingType,
                                "expireTime": self.getTimeInSeconds() + 30}
                            # print(self.buildExpansionDict)
                            action = w.move(loc)
                            self.macroActions.append(action)
                else:
                    print("SHOULD NEVER GET HERE - NOT IMPLEMENTED")
                    # build expansion (command center) closest to worker and fly it to expansion afterwards
                    pass
            else:
                # print("retrieving worker from dict")
                wTag = list(self.buildExpansionDict.keys())[0]
                w = worker or self.units.find_by_tag(wTag)
                expandInfo = self.buildExpansionDict[wTag]
                buildingType = expandInfo["buildingType"]
                if w and self.can_afford(buildingType):
                    # print("removing entry from dict")
                    expandInfo = self.buildExpansionDict.pop(wTag)
                    loc = expandInfo["location"]
                    action = w.build(buildingType, loc)
                    self.macroActions.append(action)

        else:
            # is normal building that can be built anywhere where there is room
            if not location and self.townhalls.ready.exists:
                location = self.townhalls.ready.random
                
            loc = await self.find_placement(buildingType, near=location, random_alternative=False, minDistanceToResources=3, placement_step=1)
            w = worker or self.selectWorker(loc)
            if w and loc:
                action = w.build(loc)
                self.macroActions.append(action)        

    # select workers that are mining minerals or are idle
    def selectWorker(self, pos=None, excludeTags=None):
        if not hasattr(self, "recentlySelectedWorkers"):
            self.recentlySelectedWorkers = {}
        for key in list(self.recentlySelectedWorkers.keys()): # remove expired items
            value = self.recentlySelectedWorkers[key]
            if value["expireTime"] < self.getTimeInSeconds():
                self.recentlySelectedWorkers.pop(key)

        w = None
        ws = None
        if excludeTags:
            ws = self.workers.gathering.tags_not_in(excludeTags).tags_not_in(self.recentlySelectedWorkers)
            if not ws:
                ws = self.workers.idle.tags_not_in(excludeTags).tags_not_in(self.recentlySelectedWorkers)
        elif not ws:
            ws = self.workers.gathering.tags_not_in(self.recentlySelectedWorkers)
            if not ws:
                ws = self.workers.idle.tags_not_in(self.recentlySelectedWorkers)
        if ws:
            if pos:
                w = ws.closest_to(pos)
            else:
                w = ws.random
        if w:
            self.recentlySelectedWorkers[w.tag] = {"expireTime": self.getTimeInSeconds() + 0.5}
        return w

    async def distribute_workers(self, performanceHeavy=True, onlySaturateGas=False):
        # expansion_locations = self.expansion_locations
        # owned_expansions = self.owned_expansions


        mineralTags = [x.tag for x in self.state.units.mineral_field]
        # gasTags = [x.tag for x in self.state.units.vespene_geyser]
        geyserTags = [x.tag for x in self.geysers]

        workerPool = self.units & []
        workerPoolTags = set()

        # find all geysers that have surplus or deficit
        deficitGeysers = {}
        surplusGeysers = {}
        for g in self.geysers.filter(lambda x:x.vespene_contents > 0):
            # only loop over geysers that have still gas in them
            deficit = g.ideal_harvesters - g.assigned_harvesters
            if deficit > 0:
                deficitGeysers[g.tag] = {"unit": g, "deficit": deficit}
            elif deficit < 0:
                surplusWorkers = self.workers.closer_than(10, g).filter(lambda w:w not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in geyserTags)
                # workerPool.extend(surplusWorkers)
                for i in range(-deficit):
                    if surplusWorkers.amount > 0:
                        w = surplusWorkers.pop()
                        workerPool.append(w)
                        workerPoolTags.add(w.tag)
                surplusGeysers[g.tag] = {"unit": g, "deficit": deficit}

        # find all townhalls that have surplus or deficit
        deficitTownhalls = {}
        surplusTownhalls = {}
        if not onlySaturateGas:
            for th in self.townhalls:
                deficit = th.ideal_harvesters - th.assigned_harvesters
                if deficit > 0:
                    deficitTownhalls[th.tag] = {"unit": th, "deficit": deficit}
                elif deficit < 0:
                    surplusWorkers = self.workers.closer_than(10, th).filter(lambda w:w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                    # workerPool.extend(surplusWorkers)
                    for i in range(-deficit):
                        if surplusWorkers.amount > 0:
                            w = surplusWorkers.pop()
                            workerPool.append(w)
                            workerPoolTags.add(w.tag)
                    surplusTownhalls[th.tag] = {"unit": th, "deficit": deficit}

            if all([len(deficitGeysers) == 0, len(surplusGeysers) == 0, len(surplusTownhalls) == 0 or deficitTownhalls == 0]):
                # cancel early if there is nothing to balance
                return

        # check if deficit in gas less or equal than what we have in surplus, else grab some more workers from surplus bases
        deficitGasCount = sum(gasInfo["deficit"] for gasTag, gasInfo in deficitGeysers.items() if gasInfo["deficit"] > 0)
        surplusCount = sum(-gasInfo["deficit"] for gasTag, gasInfo in surplusGeysers.items() if gasInfo["deficit"] < 0)
        surplusCount += sum(-thInfo["deficit"] for thTag, thInfo in surplusTownhalls.items() if thInfo["deficit"] < 0)

        if deficitGasCount - surplusCount > 0:
            # grab workers near the gas who are mining minerals
            for gTag, gInfo in deficitGeysers.items():
                if workerPool.amount >= deficitGasCount:
                    break
                workersNearGas = self.workers.closer_than(10, gInfo["unit"]).filter(lambda w:w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                while workersNearGas.amount > 0 and workerPool.amount < deficitGasCount:
                    w = workersNearGas.pop()
                    workerPool.append(w)
                    workerPoolTags.add(w.tag)

        # now we should have enough workers in the pool to saturate all gases, and if there are workers left over, make them mine at townhalls that have mineral workers deficit
        for gTag, gInfo in deficitGeysers.items():
            if performanceHeavy:
                # sort furthest away to closest (as the pop() function will take the last element)
                workerPool.sort(key=lambda x:x.distance_to(gInfo["unit"]), reverse=True)
            for i in range(gInfo["deficit"]):
                if workerPool.amount > 0:
                    w = workerPool.pop()
                    if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                        self.macroActions.append(w.gather(gInfo["unit"], queue=True))
                    else:
                        self.macroActions.append(w.gather(gInfo["unit"]))

        if not onlySaturateGas:
            # if we now have left over workers, make them mine at bases with deficit in mineral workers
            for thTag, thInfo in deficitTownhalls.items():
                if performanceHeavy:
                    # sort furthest away to closest (as the pop() function will take the last element)
                    workerPool.sort(key=lambda x:x.distance_to(thInfo["unit"]), reverse=True)
                for i in range(thInfo["deficit"]):
                    if workerPool.amount > 0:
                        w = workerPool.pop()
                        mf = self.state.mineral_field.closer_than(10, thInfo["unit"]).closest_to(w)
                        if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                            self.macroActions.append(w.gather(mf, queue=True))
                        else:
                            self.macroActions.append(w.gather(mf))

        # TODO: check if a drone is mining from a destroyed base (= if nearest townhalf from the GATHER target is >10 away) -> make it mine at another mineral patch

        # TODO: if we have too much gas, mine minerals again

    def chooseClosestMineralField(self, unit):        
        mfs = self.state.mineral_field.closer_than(10, unit)
        if not mfs:
            for th in self.townhalls.ready:
                mfs += self.state.mineral_field.closer_than(10, th)
        if not mfs:
            mfs = self.state.mineral_field.filter(lambda x: x.mineral_contents > 0)
        if mfs:
            mf = mfs.closest_to(unit)
            return mf
        return None

    # split workers evenly across mineral patches
    def splitWorkers(self):
        if self.allowedSplitWorkers:
            for w in self.workers:
                mf = self.chooseClosestMineralField(w)
                if mf:
                    action = w.gather(mf)
                    self.microActions.append(action)

    # send idle workers back to mining
    def handleIdleWorkers(self):
        if self.allowedHandleIdleWorkers:
            if self.townhalls.exists:
                assignedTags = []
                if hasattr(self, "buildExpansionDict") and self.buildExpansionDict:
                    assignedTags = list(self.buildExpansionDict.keys())
                # for w in self.workers.tags_not_in(assignedTags).idle:
                for w in self.units.of_type([MULE, race_worker[self.race]]).tags_not_in(assignedTags).idle:
                    th = self.townhalls.ready.closest_to(w)
                    mf = self.chooseClosestMineralField(th)
                    if mf:
                        action = w.gather(mf)
                        self.macroActions.append(action)

    # if a base got destroyed, the workers keep long distance mining from those mineral patches usually
    def handleLongDistanceMining(self):
        if self.allowedHandleLongDistanceMining:
            if self.townhalls.exists:
                for w in self.workers.gathering:
                    mfTag = w.orders[0].target
                    mf = self.state.mineral_field.find_by_tag(mfTag)
                    if mf: # worker is mining minerals
                        th = self.townhalls.closest_to(mf)
                        d = th.distance_to(mf)
                        if d > 10:
                            mf = self.chooseClosestMineralField(w)
                            self.microActions.append(w.gather(mf))

                    elif not mf: # is not mineral field, must be geyser
                        g =  self.geysers.find_by_tag(mfTag)
                        if g:
                            th = self.townhalls.closest_to(g)
                            d = th.distance_to(g)
                            if d > 10:
                                mf = self.chooseClosestMineralField(w)
                                self.microActions.append(w.gather(mf))




    # call down mules asap
    def handleMules(self):
        if self.allowedHandleMules and self.race == Race.Terran:
            for oc in self.units(UnitTypeId.ORBITALCOMMAND).ready.filter(lambda x: x.energy >= 50):
                mfs = self.state.mineral_field.closer_than(10, oc)
                if mfs: # mule the mineral patch with higehst amount
                    mf = max(mfs, key=lambda x: x.mineral_contents)
                    action = oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)
                    self.macroActions.append(action)
                else: # mule any base
                    mf = self.chooseClosestMineralField(oc)
                    if mf:
                        action = oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)
                        self.macroActions.append(action)

    # set worker rally on new townhalls
    def setWorkerRallyPoint(self):
        if self.allowedSetRallyPoints:
            if not hasattr(self, "townhallsRallyPointsIssued"):
                self.townhallsRallyPointsIssued = set()

            for th in self.townhalls.ready.tags_not_in(self.townhallsRallyPointsIssued):
                mfs = self.state.mineral_field.closer_than(10, th)
                if mfs:
                    mf = mfs.closest_to(mfs.center)
                    action = th(AbilityId.RALLY_WORKERS, mf)
                    self.macroActions.append(action)

    # lift and lower depots if we are terran and enemies are nearby
    def handleDepots(self):
        if self.allowedHandleDepots and self.race == Race.Terran:
            for depot in self.units.of_type([SUPPLYDEPOT, SUPPLYDEPOTDROP]).ready:
                if not self.known_enemy_units.closer_than(4, depot).exists:
                    action = depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
                    self.microActions.append(action)
            for depot in self.units(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
                if self.known_enemy_units.closer_than(3, depot).exists:
                    action = depot(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                    self.microActions.append(action)

    # make workers repair if we are terran
    def handleRepair(self):
        if self.allowedHandleRepairs and self.race == Race.Terran:     
            importantDefensiveBuildings = [BUNKER, PLANETARYFORTRESS, MISSILETURRET]
            # refresh alive buildings, clear assigned dead workers, make assigned alive workers repair again
            if not hasattr(self, "assignedRepairs"):
                self.assignedRepairs = {}
            for previouslyBurningTag in list(self.assignedRepairs.keys()):
                building = self.units.find_by_tag(previouslyBurningTag)
                if not building or building \
                    and (building.health_percentage >= 1 or building.type_id not in importantDefensiveBuildings and building.health_percentage >= 0.35):
                    wsTags = self.assignedRepairs.pop(previouslyBurningTag)
                    for wTag in wsTags:
                        w = self.units.find_by_tag(wTag)
                        if w:
                            self.microActions.append(w.stop())
                            # idle workers are being handled by another function    
                elif building and (building.health_percentage < 0.35 or building.type_id in importantDefensiveBuildings and building.health_percentage < 1):
                    wsTags = self.assignedRepairs[previouslyBurningTag]
                    for wTag in list(wsTags)[:]: # because we are removing while iterating over it
                        w = self.units.find_by_tag(wTag)
                        if w:
                            # make alive worker repair again if order[0] isnt repair
                            if w.is_idle or w.orders[0].ability.id not in [AbilityId.EFFECT_REPAIR]:
                                action = w(AbilityId.EFFECT_REPAIR, building)
                                self.microActions.append(action)
                        else:
                            wsTags.remove(wTag) # remove dead worker

            for burningBuilding in ( \
                self.units.structure.ready.filter(lambda x: x.health_percentage - 0.001 < 1/3) # burning buildings
                | self.units.ready.of_type(importantDefensiveBuildings).filter(lambda x: x.health_percentage < 0.8) # defensive structures
                # mechanical units close to townhalls
                ): # TODO: add mechanical units to repair list

                if burningBuilding.tag not in self.assignedRepairs:
                    self.assignedRepairs[burningBuilding.tag] = set()

                newlyAssignedWorkers = self.units & []
                if self.assignedRepairs[burningBuilding.tag] == set() and burningBuilding.type_id not in importantDefensiveBuildings:
                    # assign worker to repair
                    w = self.selectWorker(burningBuilding)
                    if w:
                        newlyAssignedWorkers.append(w)

                elif burningBuilding.type_id in importantDefensiveBuildings:
                    # assign up to 8 workers to repair important stuff
                    for i in range(8 - len(self.assignedRepairs[burningBuilding.tag])):
                        w = self.selectWorker(burningBuilding)
                        if w:
                            newlyAssignedWorkers.append(w)
                
                #  make new assigned scvs repair
                for w in newlyAssignedWorkers:                        
                    action = w(AbilityId.EFFECT_REPAIR, burningBuilding)
                    self.microActions.append(action)
                    self.assignedRepairs[burningBuilding.tag].add(w.tag)

    # cancel buildings when they are basically under attack and about to die
    def handleBuildingCancelMicro(self):
        if self.allowedBuildingCancelMicro:
            for b in self.units.structure.not_ready.filter(lambda x: x.health_percentage + 0.05 < x.build_progress and x.health_percentage < 0.1):
                self.microActions.append(b(CANCEL))

    # flies command center and orbitals closer to base - or flies to a new base if mined out!
    def handleMisplacedCommandCenter(self):
        if self.allowedFlyingCoommandCenters:
            # if self.townhalls.exists:
            if not self.units.of_type([ORBITALCOMMANDFLYING, COMMANDCENTERFLYING]).exists:
                for th in self.townhalls:
                    mfs = self.state.mineral_field.closer_than(self.baseToMineralsCenterDistance + 3, th)
                    if mfs:
                        mfsCenter = mfs.center
                        d = th.distance_to(mfsCenter)
                        if d > self.baseToMineralsCenterDistance + 1:
                            # how?
                            pass
                    elif not mfs:
                        # find a base that has no allied or enemy base nearby   
                        for exp in self.expansion_locations.keys():
                            # is dict, key contains center (Point2) and value contains all mineral fields as set?
                            pass



            else:
                for th in self.units.of_type([ORBITALCOMMANDFLYING, COMMANDCENTERFLYING]):
                    pass



    def already_pending(self, unit_type):
        # print("hellooo")
        ability = self._game_data.units[unit_type.value].creation_ability
        unitAttributes = self._game_data.units[unit_type.value].attributes

        # # the following checks for construction of buildings, i think 8 in unitAttributes stands for "structure" tag
        # # i commented the following out because i think that is not what is meant with "already pending", but rather having a worker queued up to place a building, or having units in production queue
        # if self.units(unit_type).not_ready.exists and 8 in unitAttributes:
        #     return len(self.units(unit_type).not_ready)
        # the following checks for units being made from eggs and trained units in general
        
        buildings_in_construction = self.units.structure(unit_type).not_ready  

        # a = [[ability, Point2((o.target.x, o.target.y)).rounded, s.position.rounded] for w in self.workers for o in w.orders for s in buildings_in_construction if o.ability==ability]
        # if a != []:
        #     print(a)

        if 8 not in unitAttributes and any(o.ability == ability for w in (self.units.not_structure) for o in w.orders): 
            return sum([o.ability == ability for w in (self.units - self.workers) for o in w.orders])
        # following checks for unit production in a building queue, like queen, also checks if hatch is morphing to LAIR
        elif any(o.ability.id == ability.id for w in (self.units.structure) for o in w.orders):
            return sum([o.ability.id == ability.id for w in (self.units.structure) for o in w.orders])
        # the following checks if a worker is about to start a construction (and for scvs still constructing if not checked for structures with same position as target)
        elif any(o.ability == ability for w in self.workers for o in w.orders):
            # return sum([o.ability == ability and Point2((o.target.x, o.target.y)).rounded == s.position.rounded for w in self.workers for o in w.orders for s in buildings_in_construction]) # either this one

            return sum([o.ability == ability for w in self.workers for o in w.orders]) \
                - buildings_in_construction.amount
        elif any(egg.orders[0].ability == ability for egg in self.units(EGG)):
            return sum([egg.orders[0].ability == ability for egg in self.units(EGG)])
        return 0

    def getUnitInfo(self, unit, field="food_required"):
        # get various unit data, see list below
        # usage: getUnitInfo(ROACH, "mineral_cost")
        assert isinstance(unit, (Unit, UnitTypeId))
        if isinstance(unit, Unit):
            # unit = unit.type_id
            unit = unit._type_data._proto
        else:
            unit = self._game_data.units[unit.value]._proto
        # unit = self._game_data.units[unit.value]
        # print(vars(unit)) # uncomment to get the list below
        if hasattr(unit, field):
            return getattr(unit, field)
        else:
            return None
        """
        name: "Drone"
        available: true
        cargo_size: 1
        attributes: Light
        attributes: Biological
        movement_speed: 2.8125
        armor: 0.0
        weapons {
            type: Ground
            damage: 5.0
            attacks: 1
            range: 0.10009765625
            speed: 1.5
        }
        mineral_cost: 50
        vespene_cost: 0
        food_required: 1.0
        ability_id: 1342
        race: Zerg
        build_time: 272.0
        sight_range: 8.0
        """

def main():
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Zerg, BurnyBasicAI()),
        Computer(Race.Terran, Difficulty.Medium)
    ], realtime=False)

if __name__ == '__main__':
    main()
